#!/usr/bin/env bash
#
# whitelist_sim.sh — simulate a "white list" censorship regime for testing.
#
# A whitelist regime blocks ALL outbound traffic except to an explicit allow
# list of IPs/CIDRs (the "permitted infrastructure"). This is the model PHANTOM
# must survive in CDN mode: your raw VPS IP is NOT on the list, but a CDN edge
# IP is. Run this on a CLIENT machine (a test VM/device — NOT your exit server)
# to recreate that environment and verify which connections survive.
#
# It only filters OUTPUT and keeps established connections alive, so an existing
# SSH session into the test box is not dropped. DNS to 1.1.1.1 stays open so
# names still resolve.
#
# Usage:
#   sudo ./whitelist_sim.sh on  104.16.0.0/13 [more CIDRs ...]   # enable
#   sudo ./whitelist_sim.sh off                                  # disable
#   sudo ./whitelist_sim.sh status                               # show ruleset
#   ./whitelist_sim.sh test <host>                               # probe reachability
#
# Typical test:
#   1. sudo ./whitelist_sim.sh on            # empty allow list
#   2. connect with the DIRECT uri  → must FAIL (origin IP not allowed)
#   3. sudo ./whitelist_sim.sh on <CDN_CIDR>
#   4. connect with the CDN uri     → must SUCCEED (rides whitelisted edge)

set -euo pipefail

TABLE="wlsim"
DNS_RESOLVER="${DNS_RESOLVER:-1.1.1.1}"

require_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "This command needs root. Re-run with sudo." >&2
        exit 1
    fi
}

cmd_on() {
    require_root
    local allow=("$@")

    nft delete table inet "$TABLE" 2>/dev/null || true

    nft -f - <<EOF
table inet $TABLE {
    chain output {
        type filter hook output priority 0; policy drop;

        oif "lo" accept
        ct state established,related accept

        # DNS to the permitted resolver (names must still resolve)
        ip daddr $DNS_RESOLVER udp dport 53 accept
        ip daddr $DNS_RESOLVER tcp dport 53 accept

$(for cidr in "${allow[@]:-}"; do [[ -n "$cidr" ]] && echo "        ip daddr $cidr accept"; done)
    }
}
EOF
    echo "[whitelist_sim] ENABLED. Allowed (besides lo/established/DNS):"
    if [[ ${#allow[@]} -eq 0 || -z "${allow[0]:-}" ]]; then
        echo "  (nothing — pure deny, only DNS + established survive)"
    else
        printf '  %s\n' "${allow[@]}"
    fi
}

cmd_off() {
    require_root
    nft delete table inet "$TABLE" 2>/dev/null || true
    echo "[whitelist_sim] DISABLED. All outbound traffic restored."
}

cmd_status() {
    if nft list table inet "$TABLE" 2>/dev/null; then
        :
    else
        echo "[whitelist_sim] not active."
    fi
}

cmd_test() {
    local host="${1:?usage: test <host>}"
    echo "Resolving + probing $host:443 ..."
    if timeout 8 bash -c "exec 3<>/dev/tcp/$host/443" 2>/dev/null; then
        echo "  REACHABLE  → $host:443 connected"
        exec 3>&- 2>/dev/null || true
    else
        echo "  BLOCKED    → $host:443 not reachable"
    fi
}

case "${1:-}" in
    on)     shift; cmd_on "$@" ;;
    off)    cmd_off ;;
    status) cmd_status ;;
    test)   shift; cmd_test "$@" ;;
    *)
        grep '^#' "$0" | sed 's/^# \{0,1\}//'
        exit 1
        ;;
esac
