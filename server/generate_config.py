#!/usr/bin/env python3
"""PHANTOM setup script — generates all server and client configs.

Two transports:
  reality (default) — VLESS + Vision + REALITY. No domain, no certificate,
                      no nginx. Xray binds :443 directly and borrows a real
                      site's TLS handshake. Strongest anti-DPI, full speed.
  xhttp             — VLESS + XHTTP behind nginx TLS (needs a domain + cert).

Run on the exit server after cloning the repo:
    python3 server/generate_config.py --ip 1.2.3.4                 # reality
    python3 server/generate_config.py --ip 1.2.3.4 --domain d --transport xhttp

With --apply it writes configs directly to system paths (requires root).
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import PhantomProvider, CdnRelay, RealityConfig
from core.phantom import (
    _derive_token,
    DEFAULT_REALITY_DEST,
    DEFAULT_REALITY_SNI,
    PHANTOM_CDN_ORIGIN_PORT,
    generate_cdn_uri,
    generate_direct_uri,
    generate_nginx_fallback_conf,
    generate_reality_keypair,
    generate_reality_relay_uri,
    generate_reality_uri,
    generate_reality_xray_config,
    generate_relay_stream_conf,
    generate_relay_uri,
    generate_short_id,
    generate_subscription,
    generate_xray_server_config,
    new_phantom_provider,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate PHANTOM server and client configs")
    p.add_argument("--ip",        required=True, help="Server public IP")
    p.add_argument("--transport", choices=["reality", "xhttp"], default="reality",
                   help="Transport (default: reality — no domain/cert needed)")
    p.add_argument("--domain",    default="",  help="[xhttp] Your domain (e.g. vpn.example.com)")
    p.add_argument("--users",     type=int, default=1, help="Number of user UUIDs (default: 1)")
    p.add_argument("--secret",    default="",  help="[xhttp] Master secret (auto-generated if omitted)")
    p.add_argument("--mode",      choices=["direct", "cdn", "both"], default="direct",
                   help="[xhttp] Deployment mode: direct (Xray on 443), cdn, both")
    p.add_argument("--cdn-domain",    default="", help="[xhttp/cdn] CDN domain (e.g. cdn.example.com)")
    p.add_argument("--cdn-edge-ip",   default="", help="[xhttp/cdn] CDN RU edge IP for fronting")
    p.add_argument("--fronting-sni",  default="", help="[xhttp/cdn] Fronting SNI (e.g. vk.com)")
    p.add_argument("--relay-ip",      default="", help="Domestic relay IP for whitelist entry; "
                   "also emits a whitelist client URI and relay_stream.conf (TCP passthrough to exit)")
    # REALITY-specific
    p.add_argument("--reality-dest", default=DEFAULT_REALITY_DEST,
                   help=f"[reality] Site whose TLS handshake to borrow (default: {DEFAULT_REALITY_DEST})")
    p.add_argument("--reality-sni",  default=DEFAULT_REALITY_SNI,
                   help=f"[reality] SNI / serverName, must be served by --reality-dest (default: {DEFAULT_REALITY_SNI})")
    p.add_argument("--reality-private-key", default="", help="[reality] x25519 private key (auto-generated if omitted)")
    p.add_argument("--reality-public-key",  default="", help="[reality] x25519 public key (required if private key given)")
    p.add_argument("--reality-short-id",    default="", help="[reality] shortId hex (auto-generated if omitted)")
    p.add_argument("--apply",    action="store_true",
                   help="Write configs to system paths (needs root; review output first)")
    p.add_argument("--out-dir",  default="./phantom-out",
                   help="Directory for generated files (default: ./phantom-out)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.transport == "reality":
        _main_reality(args)
    else:
        _main_xhttp(args)


# ===========================================================================
# REALITY
# ===========================================================================

def _main_reality(args: argparse.Namespace) -> None:
    provider = PhantomProvider(
        id="exit-1",
        server_ip=args.ip,
        domain=args.domain or "reality",   # unused by REALITY
        secret=args.secret or secrets.token_hex(32),
    )

    # keypair: use supplied keys, else generate (needs `cryptography`)
    if args.reality_private_key and args.reality_public_key:
        priv, pub = args.reality_private_key, args.reality_public_key
    elif args.reality_private_key or args.reality_public_key:
        sys.exit("Provide BOTH --reality-private-key and --reality-public-key, or neither")
    else:
        try:
            priv, pub = generate_reality_keypair()
        except Exception as e:
            sys.exit(
                f"Could not generate REALITY keys ({e}).\n"
                "Run `xray x25519` on the server and pass the result with\n"
                "  --reality-private-key <priv> --reality-public-key <pub>"
            )

    reality = RealityConfig(
        private_key=priv,
        public_key=pub,
        dest=args.reality_dest,
        server_name=args.reality_sni,
        short_id=args.reality_short_id or generate_short_id(),
    )

    uuids = [str(uuid.uuid4()) for _ in range(args.users)]
    xray_config = generate_reality_xray_config(uuids, reality)

    client_uris: list[str] = []
    for i, uid in enumerate(uuids):
        suffix = f"-u{i+1}" if len(uuids) > 1 else ""
        client_uris.append(generate_reality_uri(provider, reality, uid, f"PHANTOM-Reality{suffix}"))
        if args.relay_ip:
            client_uris.append(
                generate_reality_relay_uri(provider, reality, args.relay_ip, uid,
                                           f"PHANTOM-Reality-Whitelist{suffix}")
            )

    files: dict[str, str] = {
        "xray_config.json": json.dumps(xray_config, indent=2, ensure_ascii=False),
        "subscription.txt": "\n".join(client_uris),
        "subscription.b64": generate_subscription(client_uris),
        "phantom.secret": (
            f"TRANSPORT=reality\n"
            f"REALITY_PRIVATE_KEY={priv}\n"
            f"REALITY_PUBLIC_KEY={pub}\n"
            f"REALITY_DEST={reality.dest}\n"
            f"REALITY_SNI={reality.server_name}\n"
            f"REALITY_SHORT_ID={reality.short_id}\n"
        ),
    }
    if args.relay_ip:
        files["relay_stream.conf"] = generate_relay_stream_conf(provider)

    _write_files(args.out_dir, files)

    sep = "─" * 60
    print(sep)
    print("PHANTOM CONFIGURATION GENERATED")
    print(sep)
    print(f"Server IP:   {args.ip}")
    print(f"Transport:   REALITY (VLESS + Vision)")
    print(f"REALITY SNI: {reality.server_name}  (dest: {reality.dest})")
    print(f"Public key:  {pub}")
    print(f"Short ID:    {reality.short_id}")
    print(f"Users:       {len(uuids)}")
    print(f"Output dir:  {os.path.abspath(args.out_dir)}")
    print(sep)
    print("CLIENT URIS:")
    for uri in client_uris:
        print(f"  {uri}")
    print(sep)

    if args.apply:
        _apply_reality(files)


def _apply_reality(files: dict) -> None:
    if os.geteuid() != 0:
        sys.exit("--apply requires root (run with sudo)")

    xray_cfg_path = "/usr/local/etc/xray/config.json"
    os.makedirs(os.path.dirname(xray_cfg_path), exist_ok=True)
    with open(xray_cfg_path, "w") as f:
        f.write(files["xray_config.json"])
    print(f"[OK] Written Xray config → {xray_cfg_path}")

    os.makedirs("/etc/phantom", exist_ok=True)
    with open("/etc/phantom/phantom.secret", "w") as f:
        f.write(files["phantom.secret"])
    os.chmod("/etc/phantom/phantom.secret", 0o600)
    print("[OK] Written keys → /etc/phantom/phantom.secret")

    print()
    print("Next steps:")
    print("  systemctl restart xray")
    print("  # REALITY needs no nginx and no certificate.")


# ===========================================================================
# XHTTP (legacy / behind-nginx)
# ===========================================================================

def _main_xhttp(args: argparse.Namespace) -> None:
    if not args.domain:
        sys.exit("--domain is required for xhttp transport")

    if args.secret:
        provider = PhantomProvider(id="exit-1", server_ip=args.ip,
                                   domain=args.domain, secret=args.secret)
    else:
        provider = new_phantom_provider(args.ip, args.domain, provider_id="exit-1")

    token   = _derive_token(provider.secret)
    ws_path = f"/phantom/{token}"
    uuids   = [str(uuid.uuid4()) for _ in range(args.users)]

    relay: CdnRelay | None = None
    if args.mode in ("cdn", "both"):
        if not args.cdn_domain:
            sys.exit("--cdn-domain is required for CDN mode")
        relay = CdnRelay(
            cdn_domain=args.cdn_domain,
            cdn_edge_ip=args.cdn_edge_ip or args.ip,
            fronting_sni=args.fronting_sni or None,
        )

    xray_config = generate_xray_server_config(provider, uuids)
    nginx_mode  = "cdn" if args.mode == "cdn" else "direct"
    nginx_conf  = generate_nginx_fallback_conf(provider, mode=nginx_mode)

    client_uris: list[str] = []
    for i, uid in enumerate(uuids):
        suffix = f"-u{i+1}" if len(uuids) > 1 else ""
        if args.mode in ("direct", "both"):
            client_uris.append(generate_direct_uri(provider, uid, f"PHANTOM-Direct{suffix}"))
        if relay and args.mode in ("cdn", "both"):
            client_uris.append(generate_cdn_uri(provider, relay, uid, suffix))
        if args.relay_ip:
            client_uris.append(
                generate_relay_uri(provider, args.relay_ip, uid, f"PHANTOM-Whitelist{suffix}")
            )

    files: dict[str, str] = {
        "xray_config.json":    json.dumps(xray_config, indent=2, ensure_ascii=False),
        "nginx_fallback.conf": nginx_conf,
        "subscription.txt":    "\n".join(client_uris),
        "subscription.b64":    generate_subscription(client_uris),
        "phantom.secret": (
            f"TRANSPORT=xhttp\n"
            f"SECRET={provider.secret}\n"
            f"TOKEN={token}\n"
            f"WS_PATH={ws_path}\n"
        ),
    }
    if args.relay_ip:
        files["relay_stream.conf"] = generate_relay_stream_conf(provider)

    _write_files(args.out_dir, files)

    sep = "─" * 60
    print(sep)
    print("PHANTOM CONFIGURATION GENERATED")
    print(sep)
    print(f"Domain:     {args.domain}")
    print(f"Server IP:  {args.ip}")
    print(f"Transport:  XHTTP over TLS (mode={args.mode})")
    print(f"Path:       {ws_path}")
    print(f"Secret:     {provider.secret}  ← keep this safe")
    print(f"Users:      {len(uuids)}")
    print(f"Output dir: {os.path.abspath(args.out_dir)}")
    print(sep)
    print("CLIENT URIS:")
    for uri in client_uris:
        print(f"  {uri}")
    print(sep)

    if args.apply:
        _apply_xhttp(args, files)


def _apply_xhttp(args: argparse.Namespace, files: dict) -> None:
    if os.geteuid() != 0:
        sys.exit("--apply requires root (run with sudo)")

    xray_cfg_path = "/usr/local/etc/xray/config.json"
    os.makedirs(os.path.dirname(xray_cfg_path), exist_ok=True)
    with open(xray_cfg_path, "w") as f:
        f.write(files["xray_config.json"])
    print(f"[OK] Written Xray config → {xray_cfg_path}")

    nginx_site = "/etc/nginx/sites-available/phantom-fallback"
    with open(nginx_site, "w") as f:
        f.write(files["nginx_fallback.conf"])
    enabled = "/etc/nginx/sites-enabled/phantom-fallback"
    if not os.path.exists(enabled):
        os.symlink(nginx_site, enabled)
    print(f"[OK] Written nginx site → {nginx_site}")

    os.makedirs("/etc/phantom", exist_ok=True)
    with open("/etc/phantom/phantom.secret", "w") as f:
        f.write(files["phantom.secret"])
    os.chmod("/etc/phantom/phantom.secret", 0o600)
    print("[OK] Written secret → /etc/phantom/phantom.secret")

    print()
    print("Next steps:")
    print("  nginx -t && systemctl reload nginx")
    print("  systemctl restart xray")
    if args.mode == "cdn":
        print(f"  # CDN mode: point your CDN origin at HTTP 127.0.0.1:{PHANTOM_CDN_ORIGIN_PORT}")
        print("  # (the CDN terminates TLS; see server/configs/gcore_setup.md)")


# ===========================================================================

def _write_files(out_dir: str, files: dict[str, str]) -> None:
    out = os.path.abspath(out_dir)
    os.makedirs(out, exist_ok=True)
    for fname, content in files.items():
        with open(os.path.join(out, fname), "w") as f:
            f.write(content)


if __name__ == "__main__":
    main()
