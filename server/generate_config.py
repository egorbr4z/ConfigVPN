#!/usr/bin/env python3
"""PHANTOM setup script — generates all server and client configs.

Run on the exit server after cloning the repo:
    python3 server/generate_config.py --domain vpn.example.com --ip 1.2.3.4

With --apply it writes configs directly to system paths (requires root).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import PhantomProvider, CdnRelay
from core.phantom import (
    _derive_token,
    PHANTOM_CDN_ORIGIN_PORT,
    generate_cdn_uri,
    generate_direct_uri,
    generate_nginx_fallback_conf,
    generate_subscription,
    generate_xray_server_config,
    new_phantom_provider,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate PHANTOM server and client configs")
    p.add_argument("--domain",   required=True, help="Your domain (e.g. vpn.example.com)")
    p.add_argument("--ip",       required=True, help="Server public IP")
    p.add_argument("--users",    type=int, default=1, help="Number of user UUIDs to generate (default: 1)")
    p.add_argument("--secret",   default="",  help="Master secret (auto-generated if omitted)")
    p.add_argument("--mode",     choices=["direct", "cdn", "both"], default="direct",
                   help="Deployment mode: direct (Xray on 443), cdn (behind CDN), both")
    p.add_argument("--cdn-domain",    default="", help="[CDN mode] CDN domain (e.g. cdn.example.com)")
    p.add_argument("--cdn-edge-ip",   default="", help="[CDN mode] CDN RU edge IP for fronting")
    p.add_argument("--fronting-sni",  default="", help="[CDN mode] Fronting SNI (e.g. vk.com)")
    p.add_argument("--apply",    action="store_true",
                   help="Write configs to system paths (needs root; review output first)")
    p.add_argument("--out-dir",  default="./phantom-out",
                   help="Directory for generated files (default: ./phantom-out)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # --- provider ---------------------------------------------------------
    if args.secret:
        provider = PhantomProvider(
            id="exit-1",
            server_ip=args.ip,
            domain=args.domain,
            secret=args.secret,
        )
    else:
        provider = new_phantom_provider(args.ip, args.domain, provider_id="exit-1")

    token    = _derive_token(provider.secret)
    ws_path  = f"/phantom/{token}"
    uuids    = [str(uuid.uuid4()) for _ in range(args.users)]

    # --- CDN relay --------------------------------------------------------
    relay: CdnRelay | None = None
    if args.mode in ("cdn", "both"):
        if not args.cdn_domain:
            sys.exit("--cdn-domain is required for CDN mode")
        relay = CdnRelay(
            cdn_domain=args.cdn_domain,
            cdn_edge_ip=args.cdn_edge_ip or args.ip,
            fronting_sni=args.fronting_sni or None,
        )

    # --- generate ---------------------------------------------------------
    # The Xray config is identical for every mode (XHTTP on 127.0.0.1:10000);
    # only the nginx front and the client URI differ between direct and cdn.
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

    subscription = generate_subscription(client_uris)

    # --- write files ------------------------------------------------------
    out = os.path.abspath(args.out_dir)
    os.makedirs(out, exist_ok=True)

    files: dict[str, str] = {}

    files["xray_config.json"]    = json.dumps(xray_config, indent=2, ensure_ascii=False)
    files["nginx_fallback.conf"] = nginx_conf
    files["subscription.txt"]    = "\n".join(client_uris)
    files["subscription.b64"]    = subscription
    files["phantom.secret"]      = (
        f"SECRET={provider.secret}\n"
        f"TOKEN={token}\n"
        f"WS_PATH={ws_path}\n"
    )

    for fname, content in files.items():
        path = os.path.join(out, fname)
        with open(path, "w") as f:
            f.write(content)

    # --- print summary ----------------------------------------------------
    sep = "─" * 60
    print(sep)
    print("PHANTOM CONFIGURATION GENERATED")
    print(sep)
    print(f"Domain:     {args.domain}")
    print(f"Server IP:  {args.ip}")
    print(f"Mode:       {args.mode}")
    print(f"Transport:  XHTTP (xhttp) over TLS")
    print(f"Path:       {ws_path}")
    print(f"Secret:     {provider.secret}  ← keep this safe")
    print(f"Users:      {len(uuids)}")
    print(f"Output dir: {out}")
    print(sep)
    print("CLIENT URIS:")
    for uri in client_uris:
        print(f"  {uri}")
    print(sep)

    # --- apply to system paths (--apply) ----------------------------------
    if args.apply:
        _apply(args, files)


def _apply(args: argparse.Namespace, files: dict) -> None:
    if os.geteuid() != 0:
        sys.exit("--apply requires root (run with sudo)")

    # Xray config
    xray_cfg_path = "/usr/local/etc/xray/config.json"
    os.makedirs(os.path.dirname(xray_cfg_path), exist_ok=True)
    with open(xray_cfg_path, "w") as f:
        f.write(files["xray_config.json"])
    print(f"[OK] Written Xray config → {xray_cfg_path}")

    # nginx site
    nginx_site = "/etc/nginx/sites-available/phantom-fallback"
    with open(nginx_site, "w") as f:
        f.write(files["nginx_fallback.conf"])
    enabled = "/etc/nginx/sites-enabled/phantom-fallback"
    if not os.path.exists(enabled):
        os.symlink(nginx_site, enabled)
    print(f"[OK] Written nginx site → {nginx_site}")

    # Secret backup
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


if __name__ == "__main__":
    main()
