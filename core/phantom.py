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

    mode="direct"  — Xray listens on port 443 with TLS, handles fallbacks.
    mode="cdn"     — Xray listens on unix socket (doorman handles TLS / HTTP).
    """
    token = _derive_token(provider.secret)
    ws_path = f"/phantom/{token}"
    clients = [{"id": uid, "flow": "", "level": 0} for uid in user_uuids]

    if mode == "direct":
        stream = {
            "network": "ws",
            "security": "tls",
            "tlsSettings": {
                "serverName": provider.domain,
                "minVersion": "1.3",
                "certificates": [
                    {
                        "certificateFile": f"/etc/letsencrypt/live/{provider.domain}/fullchain.pem",
                        "keyFile": f"/etc/letsencrypt/live/{provider.domain}/privkey.pem",
                    }
                ],
                "alpn": ["h2", "http/1.1"],
                # fp is a CLIENT-side setting; server side just presents the cert
            },
            "wsSettings": {"path": ws_path},
        }
        inbound_listen = "0.0.0.0"
        inbound_port = provider.port

        # Fallback: any WS upgrade to wrong path → nginx (anti-probe)
        # Any non-WS request → nginx
        fallbacks = [
            {"dest": 8080, "xver": 0},              # non-WS HTTP → nginx
            {"path": "/", "dest": 8080, "xver": 0}, # wrong WS path → nginx
        ]
    else:  # cdn mode
        stream = {
            "network": "ws",
            "security": "none",
            "wsSettings": {"path": ws_path},
        }
        inbound_listen = "/tmp/phantom.sock,0666"
        inbound_port = 0      # unix socket ignores port
        fallbacks = []

    inbound: dict = {
        "tag": "phantom-inbound",
        "protocol": "vless",
        "settings": {
            "clients": clients,
            "decryption": "none",
            "fallbacks": fallbacks,
        },
        "streamSettings": stream,
    }

    if mode == "direct":
        inbound["listen"] = inbound_listen
        inbound["port"] = inbound_port
    else:
        inbound["listen"] = inbound_listen

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


def generate_nginx_fallback_conf(provider: PhantomProvider) -> str:
    """nginx.conf snippet — serves real content to active probers."""
    return f"""\
# PHANTOM anti-probe fallback for {provider.domain}
# Unauthenticated HTTP/WS requests are forwarded to a real website.
# Active probers receive a genuine HTTP response and see no VPN.

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
