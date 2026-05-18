"""V2Ray/VLESS configuration generator."""

from __future__ import annotations

import uuid
from urllib.parse import quote

from core.models import Provider


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
