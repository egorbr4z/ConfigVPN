"""PHANTOM protocol configuration generator.

Design summary
--------------
PHANTOM combines the strongest anti-detection properties of four protocols:

  • Trojan   — fallback to real web content for unauthenticated probers
  • Reality  — browser TLS fingerprint (fp=chrome) on the client side
  • VLESS    — lightweight framing, standard client support
  • (SS)     — high-entropy payload hidden inside normal-looking HTTPS

Auth mechanism
--------------
A secret WS path is used instead of a UUID payload or Cookie header:
  path = /phantom/<TOKEN>
  TOKEN = HMAC-SHA256(secret, b"phantom-v1")[:16].hex()

The path is transmitted inside TLS — invisible to DPI. Clients that do not
know TOKEN hit any other path → Xray fallback → nginx → real web content.
This is fully expressible in a standard VLESS URI (path= parameter).

Two deployment modes
--------------------
  Direct  — Xray listens on 443, handles TLS with real Let's Encrypt cert,
             built-in Xray fallbacks serve nginx for unauthenticated requests.
             No Python on the data path → full Xray throughput.
  CDN     — CDN terminates TLS, forwards HTTP/WS to the Python doorman on
             a local port, doorman checks path and pipes to Xray unix socket.
             Used for whitelist-mode bypass (CDN edge IPs are whitelisted).

True CDN fronting (optional)
-----------------------------
  If CdnRelay.fronting_sni is set, the client URI uses SNI = whitelisted domain
  while Host header = our cdn_domain (same CDN). CDN routes by Host regardless
  of SNI if it does not enforce strict SNI==Host validation.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import uuid
from urllib.parse import quote, urlencode

from core.models import CdnRelay, PhantomProvider


# Local plaintext port where Xray listens in "direct" mode. nginx terminates
# TLS on :443 and reverse-proxies the secret WebSocket path to this port.
PHANTOM_XRAY_PORT = 10000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _derive_token(secret: str) -> str:
    """Derive a 128-bit hex auth token from the master secret."""
    return hmac.new(
        hashlib.sha256(secret.encode()).digest(),
        b"phantom-v1",
        hashlib.sha256,
    ).digest()[:16].hex()


def _build_uri(
    user_uuid: str,
    address: str,
    port: int,
    sni: str,
    host: str,
    path: str,
    name: str,
    fp: str = "chrome",
) -> str:
    params = {
        "encryption": "none",
        "security":   "tls",
        "sni":        sni,
        "fp":         fp,
        "type":       "ws",
        "path":       path,
        "host":       host,
    }
    return f"vless://{user_uuid}@{address}:{port}?{urlencode(params)}#{quote(name, safe='')}"


# ---------------------------------------------------------------------------
# Public API — URI generators
# ---------------------------------------------------------------------------

def generate_direct_uri(
    provider: PhantomProvider,
    user_uuid: str | None = None,
    name: str = "PHANTOM-Direct",
    fp: str = "chrome",
) -> str:
    """VLESS URI for direct connection (Xray on port 443, real TLS cert)."""
    uid = user_uuid or str(uuid.uuid4())
    token = _derive_token(provider.secret)
    return _build_uri(
        user_uuid=uid,
        address=provider.domain,
        port=provider.port,
        sni=provider.domain,
        host=provider.domain,
        path=f"/phantom/{token}",
        name=name,
        fp=fp,
    )


def generate_cdn_uri(
    provider: PhantomProvider,
    relay: CdnRelay,
    user_uuid: str | None = None,
    name_suffix: str = "",
    fp: str = "chrome",
) -> str:
    """VLESS URI through CDN relay.

    CDN-as-proxy mode  (relay.fronting_sni is None):
        address = cdn_domain, SNI = cdn_domain, Host = cdn_domain

    True fronting mode (relay.fronting_sni is set):
        address = cdn_edge_ip, SNI = whitelisted_domain, Host = cdn_domain
    """
    uid = user_uuid or str(uuid.uuid4())
    token = _derive_token(provider.secret)

    if relay.fronting_sni:
        address = relay.cdn_edge_ip
        sni = relay.fronting_sni
        label = f"PHANTOM-Front{name_suffix}"
    else:
        address = relay.cdn_domain
        sni = relay.cdn_domain
        label = f"PHANTOM-CDN{name_suffix}"

    return _build_uri(
        user_uuid=uid,
        address=address,
        port=443,
        sni=sni,
        host=relay.cdn_domain,
        path=f"/phantom/{token}",
        name=label,
        fp=fp,
    )


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------

def generate_subscription(uris: list[str]) -> str:
    """Return a base64-encoded subscription file (Sing-box / Xray clients)."""
    return base64.b64encode("\n".join(uris).encode()).decode()


# ---------------------------------------------------------------------------
# Server-side config generators
# ---------------------------------------------------------------------------

def generate_xray_server_config(
    provider: PhantomProvider,
    user_uuids: list[str],
    *,
    mode: str = "direct",
) -> dict:
    """Return Xray JSON configuration for the exit server.

    mode="direct"  — Xray listens on a local plaintext WS port; nginx
                      terminates TLS on :443 and reverse-proxies the secret
                      path here, serving real content for everything else.
    mode="cdn"     — Xray listens on unix socket (doorman handles TLS / HTTP).

    In both modes TLS is terminated in front of Xray (by nginx or the CDN),
    never by Xray itself. This is what makes the Xray-level WebSocket fallback
    unnecessary: nginx routes the secret path to Xray and every other request
    to a real website, so the server is indistinguishable from a normal site.
    """
    token = _derive_token(provider.secret)
    ws_path = f"/phantom/{token}"
    clients = [{"id": uid, "flow": "", "level": 0} for uid in user_uuids]

    # Both modes: plaintext WebSocket behind a TLS-terminating front.
    stream = {
        "network": "ws",
        "security": "none",
        "wsSettings": {"path": ws_path},
    }

    if mode == "direct":
        inbound_listen = "127.0.0.1"
        inbound_port = PHANTOM_XRAY_PORT
    else:  # cdn mode
        inbound_listen = "/tmp/phantom.sock,0666"
        inbound_port = 0      # unix socket ignores port

    inbound: dict = {
        "tag": "phantom-inbound",
        "protocol": "vless",
        "settings": {
            "clients": clients,
            "decryption": "none",
        },
        "streamSettings": stream,
    }

    inbound["listen"] = inbound_listen
    if mode == "direct":
        inbound["port"] = inbound_port

    return {
        "log": {"loglevel": "warning", "access": "/var/log/xray/access.log"},
        "inbounds": [inbound],
        "outbounds": [
            {"protocol": "freedom", "tag": "direct", "settings": {}},
            {"protocol": "blackhole", "tag": "block"},
        ],
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                # Block access to private/loopback ranges from VPN clients
                {"type": "field", "ip": ["geoip:private"], "outboundTag": "block"},
                # Catch-all → direct. Must carry an effective matcher field
                # ("network"); recent Xray rejects rules with no fields
                # ("this rule has no effective fields").
                {"type": "field", "network": "tcp,udp", "outboundTag": "direct"},
            ],
        },
    }


def generate_nginx_fallback_conf(
    provider: PhantomProvider,
    xray_port: int = PHANTOM_XRAY_PORT,
    *,
    mode: str = "direct",
) -> str:
    """nginx site config for PHANTOM.

    mode="direct" — nginx terminates TLS on :443 and:
      • reverse-proxies the secret WebSocket path to the local Xray listener
        (the path lives inside TLS, invisible to DPI);
      • serves real web content for every other request, so active probers
        and DPI see an ordinary website and no trace of a VPN.
      HTTP :80 keeps the ACME challenge path open (for certbot renewal) and
      redirects everything else to HTTPS.

    mode="cdn"    — TLS is terminated by the CDN/doorman, so nginx is just the
      plaintext anti-probe content server the doorman forwards unauthenticated
      requests to (127.0.0.1:8080).
    """
    if mode == "cdn":
        return _nginx_cdn_fallback(provider)

    token = _derive_token(provider.secret)
    ws_path = f"/phantom/{token}"
    return f"""\
# PHANTOM TLS front for {provider.domain}
# nginx terminates TLS and routes the secret WS path to Xray; every other
# request is served as a real website (anti-probe). Generated — do not edit.

server {{
    listen 80;
    listen [::]:80;
    server_name {provider.domain};

    location /.well-known/acme-challenge/ {{ root /var/www/html; }}
    location / {{ return 301 https://$host$request_uri; }}
}}

server {{
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name {provider.domain};

    ssl_certificate     /etc/letsencrypt/live/{provider.domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{provider.domain}/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # --- Secret WebSocket path → Xray (invisible inside TLS) ---
    location = {ws_path} {{
        if ($http_upgrade != "websocket") {{ return 404; }}
        proxy_pass            http://127.0.0.1:{xray_port};
        proxy_http_version    1.1;
        proxy_set_header      Upgrade    $http_upgrade;
        proxy_set_header      Connection "upgrade";
        proxy_set_header      Host       $host;
        proxy_set_header      X-Real-IP  $remote_addr;
        proxy_set_header      X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout    300s;
        proxy_send_timeout    300s;
    }}

    # --- Anti-probe: everything else looks like a real website ---
    location / {{
        proxy_pass            https://www.iana.org;
        proxy_ssl_server_name on;
        proxy_set_header      Host            www.iana.org;
        proxy_set_header      X-Real-IP       $remote_addr;
        proxy_set_header      Accept-Encoding "";
        proxy_hide_header     X-Powered-By;
        proxy_hide_header     x-amz-id-2;
        proxy_hide_header     x-amz-request-id;
        add_header            X-Content-Type-Options "nosniff" always;
    }}
}}
"""


def _nginx_cdn_fallback(provider: PhantomProvider) -> str:
    """Plaintext anti-probe server for CDN mode (doorman forwards here)."""
    return f"""\
# PHANTOM anti-probe fallback for {provider.domain} (CDN mode)
# TLS is terminated by the CDN/doorman; this is the plaintext content server
# the doorman forwards unauthenticated requests to. Probers see a real site.

server {{
    listen 127.0.0.1:8080;
    server_name {provider.domain};

    location / {{
        proxy_pass         https://www.iana.org;
        proxy_ssl_server_name on;
        proxy_set_header   Host               www.iana.org;
        proxy_set_header   X-Real-IP          $remote_addr;
        proxy_set_header   Accept-Encoding    "";
        proxy_hide_header  X-Powered-By;
        proxy_hide_header  x-amz-id-2;
        proxy_hide_header  x-amz-request-id;
        add_header         Server             "nginx/1.24.0" always;
        add_header         X-Content-Type-Options "nosniff" always;
    }}
}}
"""


def generate_doorman_env(provider: PhantomProvider, listen_port: int = 8001) -> str:
    """Return a .env file content for the CDN-mode doorman process."""
    token = _derive_token(provider.secret)
    return f"""\
# PHANTOM Doorman environment (CDN mode)
# Place this at /etc/phantom/.env and run: python -m server.doorman

PHANTOM_SECRET={provider.secret}
PHANTOM_TOKEN={token}
PHANTOM_WS_PATH=/phantom/{token}
PHANTOM_XRAY_SOCK=/tmp/phantom.sock
PHANTOM_LISTEN_ADDR=0.0.0.0
PHANTOM_LISTEN_PORT={listen_port}
PHANTOM_NGINX_ADDR=127.0.0.1
PHANTOM_NGINX_PORT=8080
"""


# ---------------------------------------------------------------------------
# Dev helper: generate a fresh provider with a random secret
# ---------------------------------------------------------------------------

def new_phantom_provider(
    server_ip: str,
    domain: str,
    provider_id: str | None = None,
) -> PhantomProvider:
    """Generate a new PhantomProvider with a random 32-byte secret."""
    return PhantomProvider(
        id=provider_id or str(uuid.uuid4())[:8],
        server_ip=server_ip,
        domain=domain,
        secret=secrets.token_hex(32),
    )
