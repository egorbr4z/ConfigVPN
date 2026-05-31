"""V2Ray/VLESS configuration generator."""

from __future__ import annotations

import secrets
import uuid
from urllib.parse import quote, urlencode

from core.models import Provider

# Curated list of high-traffic RU-accessible domains for Reality SNI.
# Requirements: TLS 1.3, h2 ALPN, accessible from Russia, not blocked.
_REALITY_SNI_POOL = [
    "www.microsoft.com",
    "dl.google.com",
    "update.googleapis.com",
    "ajax.googleapis.com",
    "www.apple.com",
    "cdn.cloudflare.com",
]

_REALITY_FP_POOL = ["chrome", "firefox", "safari", "edge", "ios"]


def generate_vless_config(providers: list[Provider]) -> dict:
    """Generate a VLESS configuration for the given providers."""
    user_uuid = str(uuid.uuid4())
    servers = []
    connection_strings = []

    for provider in providers:
        path = quote("/vpn", safe="")
        vless_uri = (
            f"vless://{user_uuid}@{provider.server_ip}:443"
            f"?encryption=none&security=tls&type=ws&path={path}"
            f"#{quote(provider.name, safe='')}"
        )
        servers.append({
            "provider_id": provider.id,
            "provider_name": provider.name,
            "server_ip": provider.server_ip,
            "uuid": user_uuid,
            "port": 443,
            "network": "ws",
            "path": "/vpn",
            "security": "tls",
            "connection_string": vless_uri,
        })
        connection_strings.append(vless_uri)

    return {
        "uuid": user_uuid,
        "servers": servers,
        "connection_strings": connection_strings,
    }


def generate_reality_config(
    providers: list[Provider],
    reality_public_key: str,
    reality_private_key: str = "",
) -> dict:
    """Generate VLESS+Reality+Vision configs for providers.

    reality_public_key / reality_private_key are generated on the server with:
        xray x25519
    Each user gets a unique UUID and short_id for correlation resistance.
    """
    user_uuid = str(uuid.uuid4())
    servers = []
    connection_strings = []

    for provider in providers:
        sni = secrets.choice(_REALITY_SNI_POOL)
        fp  = secrets.choice(_REALITY_FP_POOL)
        sid = secrets.token_hex(secrets.choice([4, 6, 8]))  # 8, 12 or 16 hex chars

        params = {
            "encryption": "none",
            "security":   "reality",
            "sni":        sni,
            "fp":         fp,
            "pbk":        reality_public_key,
            "sid":        sid,
            "spx":        quote("/", safe=""),
            "type":       "tcp",
            "flow":       "xtls-rprx-vision",
        }
        uri = (
            f"vless://{user_uuid}@{provider.server_ip}:443"
            f"?{urlencode(params)}"
            f"#{quote(provider.name, safe='')}"
        )
        servers.append({
            "provider_id":    provider.id,
            "provider_name":  provider.name,
            "server_ip":      provider.server_ip,
            "uuid":           user_uuid,
            "port":           443,
            "security":       "reality",
            "sni":            sni,
            "fingerprint":    fp,
            "short_id":       sid,
            "flow":           "xtls-rprx-vision",
            "connection_string": uri,
        })
        connection_strings.append(uri)

    return {
        "uuid":               user_uuid,
        "servers":            servers,
        "connection_strings": connection_strings,
    }
