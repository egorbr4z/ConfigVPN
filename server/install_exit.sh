#!/usr/bin/env bash
# install_exit.sh — automated PHANTOM exit server setup (foreign server)
#
# Usage:
#   sudo bash install_exit.sh --domain vpn.example.com --ip 1.2.3.4
#   sudo bash install_exit.sh --domain vpn.example.com --ip 1.2.3.4 \
#       --secret mysecret --users 3 --relay-ip 185.1.2.3
#
# What it does:
#   1. Installs nginx + certbot + python3 + Xray (official installer)
#   2. Obtains a Let's Encrypt TLS cert for --domain
#   3. Runs generate_config.py to produce all configs
#   4. Writes configs to system paths (--apply) and sets permissions
#   5. Enables and starts nginx + xray
#   6. Prints VLESS client URIs

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
XRAY_INSTALL_SCRIPT="https://github.com/XTLS/Xray-install/raw/main/install-release.sh"

# ── argument parsing ─────────────────────────────────────────────────────────
DOMAIN=""
IP=""
SECRET=""
USERS=1
RELAY_IP=""
EMAIL="admin@${DOMAIN:-example.com}"

usage() {
    echo "Usage: sudo bash $0 --domain DOMAIN --ip IP [options]"
    echo ""
    echo "Required:"
    echo "  --domain DOMAIN      Your domain (DNS A record must already point to --ip)"
    echo "  --ip     IP          This server's public IPv4 address"
    echo ""
    echo "Optional:"
    echo "  --secret SECRET      HMAC master secret (auto-generated if omitted)"
    echo "  --users  N           Number of user UUIDs (default: 1)"
    echo "  --relay-ip IP        Domestic RF relay IP — also emits a whitelist URI"
    echo "  --email  EMAIL       Email for Let's Encrypt notifications"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --domain)   DOMAIN="$2";    shift 2 ;;
        --ip)       IP="$2";        shift 2 ;;
        --secret)   SECRET="$2";    shift 2 ;;
        --users)    USERS="$2";     shift 2 ;;
        --relay-ip) RELAY_IP="$2";  shift 2 ;;
        --email)    EMAIL="$2";     shift 2 ;;
        --help|-h)  usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

[[ -z "$DOMAIN" ]] && { echo "ERROR: --domain is required"; usage; }
[[ -z "$IP"     ]] && { echo "ERROR: --ip is required";     usage; }

[[ $EUID -ne 0 ]] && { echo "ERROR: run as root (sudo bash $0 ...)"; exit 1; }

SEP="────────────────────────────────────────────────────────────"

log()  { echo -e "\n\e[32m[+]\e[0m $*"; }
info() { echo    "    $*"; }
err()  { echo -e "\e[31m[!]\e[0m $*" >&2; exit 1; }

# ── 1. system packages ───────────────────────────────────────────────────────
log "Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    nginx \
    certbot \
    python3-certbot-nginx \
    python3 \
    python3-pip \
    curl \
    ufw \
    nftables

# Ensure nginx is stopped before certbot standalone (if needed)
systemctl stop nginx 2>/dev/null || true

# ── 2. firewall ──────────────────────────────────────────────────────────────
log "Opening firewall ports (22, 80, 443)"
ufw allow 22/tcp   2>/dev/null || true
ufw allow 80/tcp   2>/dev/null || true
ufw allow 443/tcp  2>/dev/null || true
ufw --force enable 2>/dev/null || true

# ── 3. Let's Encrypt cert ────────────────────────────────────────────────────
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"

if [[ -f "${CERT_DIR}/fullchain.pem" ]]; then
    log "TLS cert already exists at ${CERT_DIR} — skipping certbot"
else
    log "Obtaining Let's Encrypt cert for ${DOMAIN}"
    certbot certonly \
        --standalone \
        --non-interactive \
        --agree-tos \
        --email "${EMAIL}" \
        -d "${DOMAIN}" \
        || err "certbot failed — check that ${DOMAIN} resolves to ${IP} and port 80 is open"
fi

# ── 4. install Xray ──────────────────────────────────────────────────────────
if command -v xray &>/dev/null; then
    log "Xray already installed ($(xray version 2>&1 | head -1)) — skipping"
else
    log "Installing Xray via official script"
    bash <(curl -Ls "${XRAY_INSTALL_SCRIPT}") install
fi

# Xray log dir
mkdir -p /var/log/xray
chown -R nobody:nogroup /var/log/xray

# ── 5. generate configs ──────────────────────────────────────────────────────
log "Generating PHANTOM configs"

GENERATE_ARGS=(
    --domain  "$DOMAIN"
    --ip      "$IP"
    --mode    direct
    --users   "$USERS"
    --apply
    --out-dir /tmp/phantom-out
)
[[ -n "$SECRET"   ]] && GENERATE_ARGS+=(--secret   "$SECRET")
[[ -n "$RELAY_IP" ]] && GENERATE_ARGS+=(--relay-ip "$RELAY_IP")

python3 "${REPO_DIR}/server/generate_config.py" "${GENERATE_ARGS[@]}"

# ── 6. nginx — ensure http module is active + site enabled ──────────────────
log "Configuring nginx"

# Make sure the default site isn't grabbing :443 before phantom
if [[ -L /etc/nginx/sites-enabled/default ]]; then
    rm -f /etc/nginx/sites-enabled/default
    info "Removed default nginx site"
fi

nginx -t || err "nginx config test failed — check /etc/nginx/sites-available/phantom-fallback"

# ── 7. Xray cert access ──────────────────────────────────────────────────────
# Xray runs as nobody; it needs to read Let's Encrypt files.
log "Granting Xray cert access"
if command -v setfacl &>/dev/null; then
    setfacl -R -m u:nobody:rX /etc/letsencrypt/live  2>/dev/null || true
    setfacl -R -m u:nobody:rX /etc/letsencrypt/archive 2>/dev/null || true
else
    # fallback: chmod g+rx and add nobody to ssl-cert group if it exists
    chmod -R g+rX /etc/letsencrypt/live   2>/dev/null || true
    chmod -R g+rX /etc/letsencrypt/archive 2>/dev/null || true
fi

# Systemd drop-in to run Xray as root if ACL not available (last resort)
XRAY_DROPIN="/etc/systemd/system/xray.service.d"
if ! setfacl -R -m u:nobody:rX /etc/letsencrypt/live 2>/dev/null; then
    log "setfacl not available — creating systemd drop-in to run Xray as root"
    mkdir -p "${XRAY_DROPIN}"
    cat > "${XRAY_DROPIN}/20-user.conf" <<'EOF'
[Service]
User=root
EOF
fi

# ── 8. enable and start services ─────────────────────────────────────────────
log "Enabling and starting nginx + xray"
systemctl daemon-reload
systemctl enable nginx xray
systemctl restart xray
systemctl restart nginx

sleep 1

# ── 9. verify ────────────────────────────────────────────────────────────────
log "Verifying services"
if systemctl is-active --quiet nginx; then
    info "nginx    — running"
else
    err "nginx failed to start — run: journalctl -xeu nginx"
fi

if systemctl is-active --quiet xray; then
    info "xray     — running"
else
    err "xray failed to start — run: journalctl -xeu xray"
fi

LISTEN_443=$(ss -tlnp 'sport = :443' 2>/dev/null | grep -c LISTEN || true)
LISTEN_10000=$(ss -tlnp 'sport = :10000' 2>/dev/null | grep -c LISTEN || true)
info "nginx :443   — $([ "$LISTEN_443"   -gt 0 ] && echo 'listening' || echo 'NOT found')"
info "Xray  :10000 — $([ "$LISTEN_10000" -gt 0 ] && echo 'listening' || echo 'NOT found')"

# ── 10. print summary ────────────────────────────────────────────────────────
echo ""
echo "$SEP"
echo "PHANTOM EXIT SERVER — READY"
echo "$SEP"
echo "Domain   : ${DOMAIN}"
echo "IP       : ${IP}"
[[ -n "$RELAY_IP" ]] && echo "Relay IP : ${RELAY_IP}"
echo ""
echo "Client URIs (also saved in /tmp/phantom-out/subscription.txt):"
cat /tmp/phantom-out/subscription.txt
echo ""
echo "Secret backup: /etc/phantom/phantom.secret"
echo ""
echo "Quick test:"
echo "  curl -sI --http2 https://${DOMAIN} | head -2   # expect HTTP/2 200"
echo "  ss -tlnp | grep -E ':443|:10000'               # nginx + xray ports"
echo "$SEP"
