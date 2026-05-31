# Gcore CDN Setup for PHANTOM (Whitelist Bypass)

Gcore CDN has edge nodes in Moscow and St. Petersburg. In a Russian whitelist
scenario, Gcore's IP ranges are likely to be included as major infrastructure.

## Prerequisites

- A domain you control (e.g. `vpn.yourdomain.com`)
- Your exit server running PHANTOM in CDN mode (doorman on port 8001)
- Gcore free account: https://gcore.com/cdn

---

## Step 1: Create a Gcore CDN Resource

1. Log in to Gcore → **CDN** → **Create CDN resource**.
2. **Custom domain**: `vpn.yourdomain.com`
3. **Origin**: your exit server IP, port 8001, protocol HTTP
4. **Origin pull protocol**: HTTP (doorman handles plain HTTP from CDN)

---

## Step 2: Enable WebSocket Support

In the CDN resource settings:
- **WebSocket**: Enable ✓
- **HTTPS**: Enable, use Gcore's free Let's Encrypt cert for your domain
- **HTTP to HTTPS redirect**: Enable

---

## Step 3: DNS

Add a CNAME record:
```
vpn.yourdomain.com.  CNAME  <gcore-provided-cname>.
```
Gcore shows the CNAME target after creating the resource.

---

## Step 4: Generate Client Configs

```python
from core.phantom import PhantomProvider, new_phantom_provider, generate_cdn_uri
from core.models import CdnRelay

provider = PhantomProvider(
    id="exit-1",
    server_ip="YOUR_EXIT_SERVER_IP",
    domain="vpn.yourdomain.com",
    secret="YOUR_MASTER_SECRET",
)

# CDN-as-proxy (no fronting) — reliable, works on all CDNs
relay_proxy = CdnRelay(
    cdn_domain="vpn.yourdomain.com",
    cdn_edge_ip="",           # not needed in proxy mode
    fronting_sni=None,
)

# True fronting — SNI = whitelisted domain, Host = our domain on same CDN
# Only works if Gcore does not enforce SNI==Host (test empirically)
relay_front = CdnRelay(
    cdn_domain="vpn.yourdomain.com",
    cdn_edge_ip="GCORE_RU_EDGE_IP",   # find with: dig +short vpn.yourdomain.com
    fronting_sni="vk.com",            # a high-traffic domain on same CDN
)

uri_cdn   = generate_cdn_uri(provider, relay_proxy)
uri_front = generate_cdn_uri(provider, relay_front)

print("CDN proxy:", uri_cdn)
print("Fronting:", uri_front)
```

---

## Step 5: Test CDN Fronting (optional)

Check whether Gcore allows SNI mismatch:

```bash
# Get Gcore edge IP for your domain
EDGE_IP=$(dig +short vpn.yourdomain.com | head -1)

# Test: SNI = vk.com, Host = your CDN domain → expect 101 WS upgrade with token
curl -v --resolve "vk.com:443:$EDGE_IP" \
  -H "Host: vpn.yourdomain.com" \
  -H "Upgrade: websocket" \
  -H "Connection: Upgrade" \
  "https://vk.com/phantom/YOUR_TOKEN" 2>&1 | grep -E "< HTTP|< Upgrade"

# If you see "101 Switching Protocols" → fronting works on this CDN.
# If you see "421 Misdirected Request" or 400 → fronting is blocked; use proxy mode only.
```

---

## CDN Fronting — Honest Assessment

| Mode | Reliability | Requirement |
|------|-------------|-------------|
| CDN-as-proxy | High — standard CDN usage | Domain on CDN, CDN IP whitelisted |
| True fronting | Unknown — CDN-dependent | CDN must not enforce SNI==Host |

Most large CDNs (Cloudflare, AWS) block true fronting. Gcore's free tier may or
may not. The subscription includes both URIs; the client tries both and uses
whichever connects.

---

## Alternative CDN Providers with Russian Presence

| Provider | Free tier | WebSocket | RU edge | Notes |
|----------|-----------|-----------|---------|-------|
| Gcore | Yes | Yes | Moscow, SPb | Primary recommendation |
| EdgeCenter | Yes | Yes | Moscow | Gcore subsidiary |
| CDNVIDEO | No | ? | Moscow | Russian CDN, enterprise |
| VK Cloud CDN | No | ? | Moscow | Requires VK business account |
