#!/usr/bin/env bash
# install_relay.sh — automated PHANTOM domestic relay setup (RF relay server)
#
# Usage:
#   sudo bash install_relay.sh --exit-ip 1.2.3.4 --exit-domain vpn.example.com
#   sudo bash install_relay.sh --exit-ip 1.2.3.4 --exit-domain vpn.example.com \
#       --secret mysecret --port 443
#
# What it does:
#   1. Installs nginx + libnginx-mod-stream
#   2. Generates a stream (TCP passthrough) config to the exit server
#   3. Includes the config in nginx.conf at the top level (stream context)
#   4. Opens port 443 in ufw
#   5. Starts nginx
#   6. Verifies the relay can reach the exit
#
# The relay is a blind TCP passthrough — it never terminates TLS, never sees
# plaintext, and needs no certificate. All TLS is end-to-end with the exit.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# ── argument parsing ─────────────────────────────────────────────────────────
EXIT_IP=""
EXIT_DOMAIN=""
SECRET=""
PORT=443

usage() {
    echo "Usage: sudo bash $0 --exit-ip IP --exit-domain DOMAIN [options]"
    echo ""
    echo "Required:"
    echo "  --exit-ip     IP      Foreign exit server public IPv4"
    echo "  --exit-domain DOMAIN  Domain of the exit server (e.g. vpn.example.com)"
    echo ""
    echo "Optional:"
    echo "  --secret SECRET       HMAC master secret (used only to print the"
    echo "                        PHANTOM-Whitelist URI; omit if you already have it)"
    echo "  --port   PORT         Port to listen on and forward to (default: 443)"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --exit-ip)     EXIT_IP="$2";     shift 2 ;;
        --exit-domain) EXIT_DOMAIN="$2"; shift 2 ;;
        --secret)      SECRET="$2";      shift 2 ;;
        --port)        PORT="$2";        shift 2 ;;
        --help|-h)     usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

[[ -z "$EXIT_IP"     ]] && { echo "ERROR: --exit-ip is required";     usage; }
[[ -z "$EXIT_DOMAIN" ]] && { echo "ERROR: --exit-domain is required"; usage; }

[[ $EUID -ne 0 ]] && { echo "ERROR: run as root (sudo bash $0 ...)"; exit 1; }

SEP="────────────────────────────────────────────────────────────"

log()  { echo -e "\n\e[32m[+]\e[0m $*"; }
info() { echo    "    $*"; }
err()  { echo -e "\e[31m[!]\e[0m $*" >&2; exit 1; }

RELAY_CONF="/etc/nginx/phantom-relay.conf"

# ── 1. packages ──────────────────────────────────────────────────────────────
log "Installing nginx + stream module"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    nginx \
    libnginx-mod-stream \
    curl \
    netcat-openbsd \
    ufw

systemctl stop nginx 2>/dev/null || true

# ── 2. generate stream passthrough config ────────────────────────────────────
log "Writing stream passthrough config"

if [[ -n "$SECRET" ]]; then
    # Use the Python generator to get the properly formatted config
    python3 - <<PYEOF > "${RELAY_CONF}"
import sys, os
sys.path.insert(0, "${REPO_DIR}")
from core.models import PhantomProvider
from core.phantom import generate_relay_stream_conf

provider = PhantomProvider(
    id="exit-1",
    server_ip="${EXIT_IP}",
    domain="${EXIT_DOMAIN}",
    secret="${SECRET}",
    port=${PORT},
)
print(generate_relay_stream_conf(provider, listen_port=${PORT}))
PYEOF
    info "Generated from Python generator with secret"
else
    # Write the stream config directly without needing the full provider
    cat > "${RELAY_CONF}" <<EOF
# PHANTOM domestic relay (whitelist entry) — raw TCP passthrough to the exit.
# Top-level stream context. TLS stays end-to-end with the exit (${EXIT_DOMAIN}).
# This relay never terminates TLS and holds no certificate.

stream {
    server {
        listen ${PORT};
        listen [::]:${PORT};
        proxy_pass            ${EXIT_IP}:${PORT};
        proxy_connect_timeout 10s;
        proxy_timeout         300s;
    }
}
EOF
    info "Generated stream config (no secret provided — URI generation skipped)"
fi

info "Config written to ${RELAY_CONF}"

# ── 3. include in nginx.conf ─────────────────────────────────────────────────
log "Including stream config in nginx.conf"

NGINX_CONF="/etc/nginx/nginx.conf"
INCLUDE_LINE="include ${RELAY_CONF};"

if grep -qF "${RELAY_CONF}" "${NGINX_CONF}"; then
    info "include already present in nginx.conf — skipping"
else
    # Append at end of file (stream{} must be top-level, outside http{})
    echo "" >> "${NGINX_CONF}"
    echo "# PHANTOM relay passthrough" >> "${NGINX_CONF}"
    echo "${INCLUDE_LINE}" >> "${NGINX_CONF}"
    info "Added: ${INCLUDE_LINE}"
fi

# Remove the default site (its :80/:443 listener would conflict)
if [[ -L /etc/nginx/sites-enabled/default ]]; then
    rm -f /etc/nginx/sites-enabled/default
    info "Removed default nginx site"
fi

nginx -t || err "nginx config test failed — check ${RELAY_CONF} and ${NGINX_CONF}"

# ── 4. firewall ──────────────────────────────────────────────────────────────
log "Opening firewall port ${PORT}/tcp"
ufw allow 22/tcp         2>/dev/null || true
ufw allow "${PORT}/tcp"  2>/dev/null || true
ufw --force enable       2>/dev/null || true

# ── 5. start nginx ───────────────────────────────────────────────────────────
log "Starting nginx"
systemctl daemon-reload
systemctl enable nginx
systemctl restart nginx

sleep 1

if ! systemctl is-active --quiet nginx; then
    err "nginx failed to start — run: journalctl -xeu nginx"
fi

# ── 6. verify relay → exit connectivity ─────────────────────────────────────
log "Testing relay → exit connectivity"

if nc -z -w 5 "${EXIT_IP}" "${PORT}" 2>/dev/null; then
    info "nc -z ${EXIT_IP}:${PORT} — REACHABLE"
else
    echo ""
    echo "WARNING: relay cannot reach ${EXIT_IP}:${PORT}"
    echo "         Check that the exit server is running and port ${PORT} is open."
    echo "         The relay config is installed correctly — fix connectivity separately."
fi

LISTEN_PORT=$(ss -tlnp "sport = :${PORT}" 2>/dev/null | grep -c LISTEN || true)
info "nginx :${PORT} — $([ "$LISTEN_PORT" -gt 0 ] && echo 'listening' || echo 'NOT found')"

# ── 7. print summary ─────────────────────────────────────────────────────────
RELAY_IP=$(curl -s4 --max-time 5 ifconfig.me 2>/dev/null || echo "<relay-ip>")

echo ""
echo "$SEP"
echo "PHANTOM RELAY SERVER — READY"
echo "$SEP"
echo "Relay IP  : ${RELAY_IP}"
echo "Exit IP   : ${EXIT_IP}"
echo "Exit domain: ${EXIT_DOMAIN}"
echo "Port      : ${PORT}"
echo ""
echo "The relay forwards raw TLS to the exit — no cert, no decryption."
echo ""
echo "Next steps:"
echo "  1. On the EXIT server, regenerate configs with --relay-ip ${RELAY_IP}:"
echo "       python3 server/generate_config.py \\"
echo "           --domain ${EXIT_DOMAIN} --ip ${EXIT_IP} \\"
[[ -n "$SECRET" ]] && echo "           --secret ${SECRET} \\" || true
echo "           --relay-ip ${RELAY_IP} --apply"
echo ""
echo "  2. Distribute the PHANTOM-Whitelist URI from the exit server's output"
echo "     (or /tmp/phantom-out/subscription.txt) to clients."
echo ""
echo "Verify from a client (simulating whitelist):"
echo "  curl -sI --resolve ${EXIT_DOMAIN}:${PORT}:${RELAY_IP} \\"
echo "       https://${EXIT_DOMAIN} | head -1   # expect HTTP/2 200"
echo "$SEP"
