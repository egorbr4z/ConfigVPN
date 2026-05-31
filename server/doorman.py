"""PHANTOM Doorman — CDN-mode HTTP front-door for Xray.

Usage
-----
    PHANTOM_SECRET=... python -m server.doorman
    # or with a .env file:
    set -a && source /etc/phantom/.env && set +a && python -m server.doorman

Role
----
CDN terminates TLS; the CDN origin (this process) receives plain HTTP.
The doorman:
  1. Reads the HTTP request headers.
  2. Checks the WS path == /phantom/<TOKEN>.
  3. Authenticated  → upgrades to WS, pipes raw stream to Xray unix socket.
  4. Unauthenticated → proxies full request to nginx (anti-probe: real content).

Python only participates in the initial connection setup (~500 bytes of headers).
After the WS upgrade is established, the OS pipes the two sockets together via
raw asyncio stream copy — Python's GIL and per-byte overhead are irrelevant.
The bottleneck is the Xray process and the CDN link, not the doorman.

Environment variables
---------------------
  PHANTOM_SECRET      Master secret (required).
  PHANTOM_WS_PATH     Full WS path including token (optional, derived from secret).
  PHANTOM_XRAY_SOCK   Xray unix socket path  (default: /tmp/phantom.sock).
  PHANTOM_LISTEN_ADDR Listen address          (default: 0.0.0.0).
  PHANTOM_LISTEN_PORT Listen port             (default: 8001).
  PHANTOM_NGINX_ADDR  nginx fallback address  (default: 127.0.0.1).
  PHANTOM_NGINX_PORT  nginx fallback port     (default: 8080).
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import logging
import os
import sys

logger = logging.getLogger("phantom.doorman")


# ---------------------------------------------------------------------------
# Config (from environment)
# ---------------------------------------------------------------------------

def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        sys.exit(f"[phantom.doorman] Missing required env var: {key}")
    return val


def _derive_token(secret: str) -> str:
    return hmac.new(
        hashlib.sha256(secret.encode()).digest(),
        b"phantom-v1",
        hashlib.sha256,
    ).digest()[:16].hex()


_SECRET      = _require("PHANTOM_SECRET")
_TOKEN       = os.environ.get("PHANTOM_WS_PATH") or f"/phantom/{_derive_token(_SECRET)}"
_XRAY_SOCK   = os.environ.get("PHANTOM_XRAY_SOCK",   "/tmp/phantom.sock")
_LISTEN_ADDR = os.environ.get("PHANTOM_LISTEN_ADDR",  "0.0.0.0")
_LISTEN_PORT = int(os.environ.get("PHANTOM_LISTEN_PORT", "8001"))
_NGINX_ADDR  = os.environ.get("PHANTOM_NGINX_ADDR",   "127.0.0.1")
_NGINX_PORT  = int(os.environ.get("PHANTOM_NGINX_PORT", "8080"))

# The secret WS path as bytes for fast comparison
_AUTH_PATH_BYTES = _TOKEN.encode() if _TOKEN.startswith(b"") else _TOKEN.encode()


# ---------------------------------------------------------------------------
# Stream helpers
# ---------------------------------------------------------------------------

async def _pipe(src: asyncio.StreamReader, dst: asyncio.StreamWriter) -> None:
    """Copy src → dst until EOF or connection error."""
    try:
        while True:
            chunk = await src.read(65536)
            if not chunk:
                break
            dst.write(chunk)
            await dst.drain()
    except (ConnectionResetError, BrokenPipeError, OSError):
        pass
    finally:
        with contextlib.suppress(Exception):
            dst.close()
            await dst.wait_closed()


# ---------------------------------------------------------------------------
# Header parsing
# ---------------------------------------------------------------------------

_MAX_HEADER_SIZE = 16_384  # 16 KB


async def _read_headers(reader: asyncio.StreamReader) -> bytes | None:
    """Read HTTP request headers up to \\r\\n\\r\\n.  Returns None on error."""
    buf = bytearray()
    try:
        while b"\r\n\r\n" not in buf:
            chunk = await asyncio.wait_for(reader.read(4096), timeout=15)
            if not chunk:
                return None
            buf.extend(chunk)
            if len(buf) > _MAX_HEADER_SIZE:
                return None
    except asyncio.TimeoutError:
        return None
    return bytes(buf)


def _parse_request_line(headers_raw: bytes) -> tuple[str, str, str]:
    """Return (method, path, version) from the first header line."""
    first_line = headers_raw.split(b"\r\n", 1)[0]
    parts = first_line.split(b" ", 2)
    if len(parts) < 3:
        return ("", "", "")
    return (
        parts[0].decode(errors="replace"),
        parts[1].decode(errors="replace"),
        parts[2].decode(errors="replace"),
    )


def _is_websocket_upgrade(headers_raw: bytes) -> bool:
    lower = headers_raw.lower()
    return b"upgrade: websocket" in lower or b"upgrade:websocket" in lower


def _is_authenticated(path: str) -> bool:
    """Constant-time check of the WS path against the derived token path."""
    return hmac.compare_digest(path.encode(), _AUTH_PATH_BYTES)


# ---------------------------------------------------------------------------
# Connection handlers
# ---------------------------------------------------------------------------

async def _handle_authenticated(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    preamble: bytes,
) -> None:
    """Pipe authenticated client to Xray unix socket (raw stream)."""
    try:
        xray_reader, xray_writer = await asyncio.open_unix_connection(_XRAY_SOCK)
    except OSError as exc:
        logger.error("Cannot connect to Xray socket %s: %s", _XRAY_SOCK, exc)
        with contextlib.suppress(Exception):
            client_writer.close()
        return

    # Forward the buffered HTTP headers (WS upgrade request) to Xray.
    # Xray sees a normal WS upgrade and responds with 101.
    # After that, both sides do raw stream copy — Python is off the data path.
    xray_writer.write(preamble)
    await xray_writer.drain()

    await asyncio.gather(
        _pipe(client_reader, xray_writer),
        _pipe(xray_reader, client_writer),
        return_exceptions=True,
    )


async def _handle_fallback(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    preamble: bytes,
) -> None:
    """Forward unauthenticated request to nginx (returns real web content)."""
    try:
        ng_reader, ng_writer = await asyncio.open_connection(_NGINX_ADDR, _NGINX_PORT)
        ng_writer.write(preamble)
        await ng_writer.drain()
        # Pipe remaining request body + full nginx response back to client
        await asyncio.gather(
            _pipe(client_reader, ng_writer),
            _pipe(ng_reader, client_writer),
            return_exceptions=True,
        )
    except OSError:
        # nginx is down — return a minimal but convincing HTTP response
        body = b"<html><body><h1>Service Unavailable</h1></body></html>"
        response = (
            b"HTTP/1.1 503 Service Unavailable\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"Server: nginx/1.24.0\r\n"
            b"Connection: close\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body
        )
        with contextlib.suppress(Exception):
            client_writer.write(response)
            await client_writer.drain()
    finally:
        with contextlib.suppress(Exception):
            client_writer.close()
            await client_writer.wait_closed()


# ---------------------------------------------------------------------------
# Main connection dispatcher
# ---------------------------------------------------------------------------

async def _handle_connection(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
) -> None:
    peer = client_writer.get_extra_info("peername", ("?", 0))
    try:
        headers_raw = await _read_headers(client_reader)
        if not headers_raw:
            return

        method, path, _ = _parse_request_line(headers_raw)
        is_ws = _is_websocket_upgrade(headers_raw)

        if is_ws and _is_authenticated(path):
            logger.debug("Authenticated WS from %s → Xray", peer[0])
            await _handle_authenticated(client_reader, client_writer, headers_raw)
        else:
            logger.debug("Fallback %s %s from %s → nginx", method, path, peer[0])
            await _handle_fallback(client_reader, client_writer, headers_raw)

    except Exception as exc:
        logger.debug("Connection error from %s: %s", peer[0], exc)
    finally:
        with contextlib.suppress(Exception):
            client_writer.close()
            await client_writer.wait_closed()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def _main() -> None:
    server = await asyncio.start_server(
        _handle_connection,
        _LISTEN_ADDR,
        _LISTEN_PORT,
    )
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    logger.info("PHANTOM Doorman listening on %s", addrs)
    logger.info("Auth path: %s", _TOKEN)
    logger.info("Xray socket: %s", _XRAY_SOCK)
    logger.info("nginx fallback: %s:%d", _NGINX_ADDR, _NGINX_PORT)

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    asyncio.run(_main())
