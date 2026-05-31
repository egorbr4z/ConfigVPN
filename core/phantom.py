"""PHANTOM protocol configuration generator.

Design summary
--------------
PHANTOM combines the strongest anti-detection properties of four protocols:

  • Trojan   — fallback to real web content for unauthenticated probers
  • Reality  — browser TLS fingerprint (fp=chrome) on the client side
  • VLESS    — lightweight framing, standard client support
  • (SS)     — high-entropy payload hidden inside normal-looking HTTPS

Transport
---------
PHANTOM uses Xray's XHTTP transport (network="xhttp") over TLS. XHTTP rides
on ordinary HTTP/2 (or HTTP/1.1) requests, so it passes cleanly through CDNs
and reverse proxies, and — unlike the older WebSocket transport — is not
deprecated in current Xray.

Auth mechanism
--------------
A secret HTTP path is used instead of a UUID payload or Cookie header:
  path = /phantom/<TOKEN>
  TOKEN = HMAC-SHA256(secret, b"phantom-v1")[:16].hex()

The path is transmitted inside TLS — invisible to DPI. Requests to any other
path are served real web content by nginx (anti-probe). This is fully
expressible in a standard VLESS URI (type=xhttp, path= parameter).

Two deployment modes
--------------------
  Direct  — nginx terminates TLS on :443 with a real Let's Encrypt cert and
             reverse-proxies the secret path to a local Xray XHTTP listener;
             every other path is served real web content (anti-probe).
  CDN     — the CDN terminates TLS and origin-pulls plain HTTP from nginx on
             a local port (default 8080); nginx does the same path routing.
             Used for whitelist-mode bypass (CDN edge IPs are whitelisted).

In both modes nginx does the path routing and Xray speaks plaintext XHTTP on
127.0.0.1:10000 — no Python on the data path.

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


# Local plaintext port where Xray listens for XHTTP. nginx (direct mode) or
# the CDN origin nginx (cdn mode) reverse-proxies the secret path to this port.
PHANTOM_XRAY_PORT = 10000

# Local plaintext HTTP port nginx exposes in "cdn" mode for the CDN to
# origin-pull from (the CDN terminates TLS, so this port serves plain HTTP).
PHANTOM_CDN_ORIGIN_PORT = 8080


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
    mode: str = "packet-up",
) -> str:
    params = {
        "encryption": "none",
        "security":   "tls",
        "sni":        sni,
        "fp":         fp,
        "type":       "xhttp",
        "mode":       mode,
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

    The Xray config is identical for both deployment modes: Xray speaks
    plaintext XHTTP on 127.0.0.1:10000. TLS is always terminated in front of
    Xray (by nginx in direct mode, by the CDN in cdn mode), and nginx routes
    the secret path here while serving real web content for everything else.
    The ``mode`` argument is accepted for symmetry with the other generators.
    """
    token = _derive_token(provider.secret)
    path = f"/phantom/{token}"
    clients = [{"id": uid, "flow": "", "level": 0} for uid in user_uuids]

    # XHTTP over plaintext, behind a TLS-terminating front (nginx / CDN).
    stream = {
        "network": "xhttp",
        "security": "none",
        "xhttpSettings": {
            "path": path,
            "mode": "auto",
        },
    }

    inbound: dict = {
        "tag": "phantom-inbound",
        "listen": "127.0.0.1",
        "port": PHANTOM_XRAY_PORT,
        "protocol": "vless",
        "settings": {
            "clients": clients,
            "decryption": "none",
        },
        "streamSettings": stream,
    }

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


def _nginx_routing_locations(ws_path: str, xray_port: int) -> str:
    """The two location blocks shared by direct and cdn nginx configs.

    The secret path (prefix match — XHTTP appends session sub-paths) is
    reverse-proxied to the local Xray XHTTP listener; everything else is
    served real web content for anti-probe. Buffering is disabled so XHTTP's
    streaming up/down requests are not stalled by nginx.
    """
    return f"""\
    # --- Secret XHTTP path → Xray (invisible inside TLS) ---
    # XHTTP packet-up rides on plain HTTP/1.1 requests, so buffering must be
    # off in both directions for the up POSTs and the long-lived down GET.
    location {ws_path} {{
        proxy_pass              http://127.0.0.1:{xray_port};
        proxy_http_version      1.1;
        proxy_set_header        Host            $host;
        proxy_set_header        X-Real-IP       $remote_addr;
        proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header        Connection      "";
        proxy_buffering         off;
        proxy_request_buffering off;
        client_max_body_size    0;
        proxy_read_timeout      300s;
        proxy_send_timeout      300s;
    }}

    # --- Anti-probe: everything else looks like a real website ---
    # proxy_pass uses a variable so nginx resolves at runtime via the resolver
    # below; ipv6=off avoids picking an AAAA the server can't reach.
    location / {{
        resolver              1.1.1.1 8.8.8.8 ipv6=off valid=300s;
        set $phantom_fallback "www.iana.org";
        proxy_pass            https://$phantom_fallback;
        proxy_ssl_server_name on;
        proxy_ssl_name        www.iana.org;
        proxy_set_header      Host            www.iana.org;
        proxy_set_header      X-Real-IP       $remote_addr;
        proxy_set_header      Accept-Encoding "";
        proxy_hide_header     X-Powered-By;
        proxy_hide_header     x-amz-id-2;
        proxy_hide_header     x-amz-request-id;
        proxy_hide_header     CF-Ray;
        proxy_hide_header     CF-Cache-Status;
        add_header            X-Content-Type-Options "nosniff" always;
    }}"""


def generate_nginx_fallback_conf(
    provider: PhantomProvider,
    xray_port: int = PHANTOM_XRAY_PORT,
    *,
    mode: str = "direct",
) -> str:
    """nginx site config for PHANTOM.

    mode="direct" — nginx terminates TLS on :443 and reverse-proxies the
      secret XHTTP path to the local Xray listener (the path lives inside TLS,
      invisible to DPI); every other request is served real web content, so
      active probers and DPI see an ordinary website and no trace of a VPN.
      HTTP :80 keeps the ACME challenge path open (for certbot renewal) and
      redirects everything else to HTTPS.

    mode="cdn"    — TLS is terminated by the CDN; nginx serves plain HTTP on
      127.0.0.1:{PHANTOM_CDN_ORIGIN_PORT} for the CDN to origin-pull from and
      does the same path routing (secret path → Xray, else → real content).
    """
    token = _derive_token(provider.secret)
    ws_path = f"/phantom/{token}"
    locations = _nginx_routing_locations(ws_path, xray_port)

    if mode == "cdn":
        return f"""\
# PHANTOM CDN origin for {provider.domain}
# The CDN terminates TLS and origin-pulls plain HTTP from this port. nginx
# routes the secret XHTTP path to Xray and serves a real site for everything
# else (anti-probe). Generated — do not edit.

server {{
    listen 127.0.0.1:{PHANTOM_CDN_ORIGIN_PORT};
    server_name {provider.domain};

{locations}
}}
"""

    return f"""\
# PHANTOM TLS front for {provider.domain}
# nginx terminates TLS and routes the secret XHTTP path to Xray; every other
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
    http2 on;                       # XHTTP clients speak HTTP/2 over TLS
    server_name {provider.domain};

    ssl_certificate     /etc/letsencrypt/live/{provider.domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{provider.domain}/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

{locations}
}}
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
