#!/usr/bin/env bash
# install_exit.sh — automated PHANTOM exit server setup (foreign server)
#
# Default transport is REALITY: no domain, no certificate, no nginx.
# Xray binds :443 directly and borrows a real site's TLS handshake.
#
# Usage (REALITY — recommended):
#   sudo bash install_exit.sh --ip 1.2.3.4
#   sudo bash install_exit.sh --ip 1.2.3.4 --users 3 --relay-ip 185.1.2.3
#   sudo bash install_exit.sh --ip 1.2.3.4 --reality-sni www.cloudflare.com \
#       --reality-dest www.cloudflare.com:443
#
# Usage (XHTTP — needs a domain + cert + nginx):
#   sudo bash install_exit.sh --ip 1.2.3.4 --transport xhttp --domain vpn.example.com
#
# REALITY flow:  Xray (official) → x25519 keys → generate_config.py --apply → start xray
# XHTTP  flow:   nginx + certbot + Xray

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
XRAY_INSTALL_SCRIPT="https://github.com/XTLS/Xray-install/raw/main/install-release.sh"

# ── argument parsing ─────────────────────────────────────────────────────────
TRANSPORT="reality"
IP=""
DOMAIN=""
SECRET=""
USERS=1
RELAY_IP=""
EMAIL=""
REALITY_SNI="www.microsoft.com"
REALITY_DEST="www.microsoft.com:443"

usage() {
    echo "Usage: sudo bash $0 --ip IP [options]"
    echo ""
    echo "Required:"
    echo "  --ip IP                This server's public IPv4 address"
    echo ""
    echo "Transport (default: reality):"
    echo "  --transport reality|xhttp"
    echo ""
    echo "REALITY options:"
    echo "  --reality-sni  HOST    SNI to borrow (default: www.microsoft.com)"
    echo "  --reality-dest HOST:PT dest site (default: www.microsoft.com:443)"
    echo ""
    echo "XHTTP options (only with --transport xhttp):"
    echo "  --domain DOMAIN        Your domain (DNS A record must point to --ip)"
    echo "  --secret SECRET        HMAC master secret (auto-generated if omitted)"
    echo "  --email  EMAIL         Email for Let's Encrypt notifications"
    echo ""
    echo "Common options:"
    echo "  --users  N             Number of user UUIDs (default: 1)"
    echo "  --relay-ip IP          Domestic RF relay IP — also emits a whitelist URI"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --transport)    TRANSPORT="$2";    shift 2 ;;
        --ip)           IP="$2";           shift 2 ;;
        --domain)       DOMAIN="$2";       shift 2 ;;
        --secret)       SECRET="$2";       shift 2 ;;
        --users)        USERS="$2";        shift 2 ;;
        --relay-ip)     RELAY_IP="$2";     shift 2 ;;
        --email)        EMAIL="$2";        shift 2 ;;
        --reality-sni)  REALITY_SNI="$2";  shift 2 ;;
        --reality-dest) REALITY_DEST="$2"; shift 2 ;;
        --help|-h)      usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

[[ -z "$IP" ]] && { echo "ERROR: --ip is required"; usage; }
[[ $EUID -ne 0 ]] && { echo "ERROR: run as root (sudo bash $0 ...)"; exit 1; }
[[ "$TRANSPORT" == "xhttp" && -z "$DOMAIN" ]] && { echo "ERROR: --domain is required for xhttp"; usage; }
EMAIL="${EMAIL:-admin@${DOMAIN:-example.com}}"

SEP="────────────────────────────────────────────────────────────"
log()  { echo -e "\n\e[32m[+]\e[0m $*"; }
info() { echo    "    $*"; }
err()  { echo -e "\e[31m[!]\e[0m $*" >&2; exit 1; }

# ── 1. install Xray (always) ─────────────────────────────────────────────────
log "Installing Xray"
if command -v xray &>/dev/null; then
    info "already installed ($(xray version 2>&1 | head -1))"
else
    bash <(curl -Ls "${XRAY_INSTALL_SCRIPT}") install
fi

# Xray log dir — owned by root since Xray runs as root
mkdir -p /var/log/xray
chown -R root:root /var/log/xray

# Run Xray as root (binds :443, reads any cert without permission issues)
log "Configuring Xray to run as root"
XRAY_DROPIN="/etc/systemd/system/xray.service.d"
mkdir -p "${XRAY_DROPIN}"
cat > "${XRAY_DROPIN}/20-user.conf" <<'EOF'
[Service]
User=root
EOF

# ── 2. firewall ──────────────────────────────────────────────────────────────
log "Opening firewall ports"
apt-get install -y -qq ufw >/dev/null 2>&1 || true
ufw allow 22/tcp   2>/dev/null || true
ufw allow 443/tcp  2>/dev/null || true
[[ "$TRANSPORT" == "xhttp" ]] && ufw allow 80/tcp 2>/dev/null || true
ufw --force enable 2>/dev/null || true

# ═════════════════════════════════════════════════════════════════════════════
if [[ "$TRANSPORT" == "reality" ]]; then
# ═════════════════════════════════════════════════════════════════════════════

    # REALITY x25519 keypair (via xray — no Python deps needed).
    # Output labels vary across Xray versions ("Private key:" / "PrivateKey:" /
    # "Password:"), but both keys are always 43-char base64url and the private
    # key is printed first — so extract by pattern, not by label.
    log "Generating REALITY x25519 keypair"
    KEYS=$(xray x25519)
    mapfile -t K < <(echo "$KEYS" | grep -oE '[A-Za-z0-9_-]{43}')
    PRIV="${K[0]:-}"; PUB="${K[1]:-}"
    [[ -z "$PRIV" || -z "$PUB" ]] && err "could not parse keys from: $KEYS"
    info "public key: $PUB"

    log "Generating PHANTOM REALITY config"
    GEN_ARGS=(
        --ip "$IP" --transport reality --users "$USERS"
        --reality-sni "$REALITY_SNI" --reality-dest "$REALITY_DEST"
        --reality-private-key "$PRIV" --reality-public-key "$PUB"
        --apply --out-dir /tmp/phantom-out
    )
    [[ -n "$RELAY_IP" ]] && GEN_ARGS+=(--relay-ip "$RELAY_IP")
    python3 "${REPO_DIR}/server/generate_config.py" "${GEN_ARGS[@]}"

    log "Starting Xray"
    systemctl daemon-reload
    systemctl enable xray
    systemctl restart xray
    sleep 1
    systemctl is-active --quiet xray || err "xray failed to start — run: journalctl -xeu xray"

    LISTEN_443=$(ss -tlnp 'sport = :443' 2>/dev/null | grep -c LISTEN || true)
    info "Xray :443 — $([ "$LISTEN_443" -gt 0 ] && echo 'listening' || echo 'NOT found')"

    echo ""
    echo "$SEP"
    echo "PHANTOM EXIT SERVER — READY (REALITY)"
    echo "$SEP"
    echo "IP          : ${IP}"
    echo "REALITY SNI : ${REALITY_SNI}  (dest: ${REALITY_DEST})"
    [[ -n "$RELAY_IP" ]] && echo "Relay IP    : ${RELAY_IP}"
    echo ""
    echo "Client URIs (also in /tmp/phantom-out/subscription.txt):"
    cat /tmp/phantom-out/subscription.txt
    echo ""
    echo "Keys backup : /etc/phantom/phantom.secret"
    echo ""
    echo "Quick test  : ss -tlnp | grep :443     # xray listening"
    echo "$SEP"

# ═════════════════════════════════════════════════════════════════════════════
else   # xhttp
# ═════════════════════════════════════════════════════════════════════════════

    log "Installing nginx + certbot"
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq nginx certbot python3-certbot-nginx python3 curl
    systemctl stop nginx 2>/dev/null || true

    CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
    if [[ -f "${CERT_DIR}/fullchain.pem" ]]; then
        log "TLS cert already exists — skipping certbot"
    else
        log "Obtaining Let's Encrypt cert for ${DOMAIN}"
        certbot certonly --standalone --non-interactive --agree-tos \
            --email "${EMAIL}" -d "${DOMAIN}" \
            || err "certbot failed — check ${DOMAIN} resolves to ${IP} and port 80 is open"
    fi

    log "Generating PHANTOM XHTTP config"
    GEN_ARGS=(
        --ip "$IP" --transport xhttp --domain "$DOMAIN" --mode direct
        --users "$USERS" --apply --out-dir /tmp/phantom-out
    )
    [[ -n "$SECRET"   ]] && GEN_ARGS+=(--secret   "$SECRET")
    [[ -n "$RELAY_IP" ]] && GEN_ARGS+=(--relay-ip "$RELAY_IP")
    python3 "${REPO_DIR}/server/generate_config.py" "${GEN_ARGS[@]}"

    log "Configuring nginx"
    [[ -L /etc/nginx/sites-enabled/default ]] && rm -f /etc/nginx/sites-enabled/default
    nginx -t || err "nginx config test failed — check /etc/nginx/sites-available/phantom-fallback"

    log "Enabling and starting nginx + xray"
    systemctl daemon-reload
    systemctl enable nginx xray
    systemctl restart xray
    systemctl restart nginx
    sleep 1
    systemctl is-active --quiet nginx || err "nginx failed to start — run: journalctl -xeu nginx"
    systemctl is-active --quiet xray  || err "xray failed to start — run: journalctl -xeu xray"

    echo ""
    echo "$SEP"
    echo "PHANTOM EXIT SERVER — READY (XHTTP)"
    echo "$SEP"
    echo "Domain : ${DOMAIN}"
    echo "IP     : ${IP}"
    [[ -n "$RELAY_IP" ]] && echo "Relay  : ${RELAY_IP}"
    echo ""
    echo "Client URIs (also in /tmp/phantom-out/subscription.txt):"
    cat /tmp/phantom-out/subscription.txt
    echo ""
    echo "Quick test: curl -sI --http2 https://${DOMAIN} | head -2"
    echo "$SEP"

fi
