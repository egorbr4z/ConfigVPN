# Gcore CDN Setup for PHANTOM

> **Reality check.** A *foreign* CDN only helps against **blacklist / DPI**
> censorship, where disguising the traffic is what matters. It does **not**
> survive a **whitelist** regime: if the CDN's edge IPs are foreign and/or
> unreachable in the region (e.g. Gcore is not available in RF), traffic never
> reaches them regardless of disguise. For whitelist bypass use a **domestic
> TCP relay** instead — see `whitelist_relay.md`. Keep this guide only for the
> blacklist/DPI case or where a CDN's edges are genuinely reachable + allowed.

Gcore CDN has edge nodes in Moscow and St. Petersburg. Where those edges are
reachable, traffic to a Gcore edge IP can pass while your raw origin IP is
filtered by DPI.

PHANTOM uses the **XHTTP** transport, which rides on ordinary HTTP/2 requests
and passes cleanly through CDNs. On the origin, **nginx** does the path routing
(secret path → Xray, everything else → a real website). There is no Python
doorman anymore.

```
client → Gcore edge (TLS, whitelisted IP) → origin nginx :8080 (HTTP)
           ├─ /phantom/<token>  → Xray (127.0.0.1:10000, xhttp)
           └─ everything else   → real website (anti-probe)
```

## Prerequisites

- A domain you control (e.g. `vpn.yourdomain.com`)
- Your exit server running PHANTOM in CDN mode (origin nginx on port 8080)
- Gcore free account: https://gcore.com/cdn

---

## Step 1: Deploy the origin in CDN mode

```bash
cd /opt/phantom
IP=$(curl -s4 ifconfig.me)
python3 server/generate_config.py \
    --domain vpn.yourdomain.com --ip "$IP" \
    --mode cdn --cdn-domain vpn.yourdomain.com --apply

nginx -t && systemctl reload nginx     # nginx now serves HTTP on 127.0.0.1:8080
systemctl restart xray                 # Xray xhttp on 127.0.0.1:10000
```

The CDN must reach the origin nginx. Bind it publicly (edit the generated site
to `listen <SERVER_IP>:8080;`) or, preferably, restrict the firewall so only
Gcore origin-pull ranges can hit port 8080.

---

## Step 2: Create a Gcore CDN Resource

1. Log in to Gcore → **CDN** → **Create CDN resource**.
2. **Custom domain**: `vpn.yourdomain.com`
3. **Origin**: your exit server IP, port `8080`, protocol **HTTP**
4. **Origin pull protocol**: HTTP (origin nginx serves plain HTTP)

---

## Step 3: Enable HTTP/2 + HTTPS

In the CDN resource settings:
- **HTTPS**: Enable, use Gcore's free Let's Encrypt cert for your domain
- **HTTP/2**: Enable (XHTTP prefers H2)
- **HTTP to HTTPS redirect**: Enable
- **Websockets**: not required for XHTTP, but enabling it does no harm

---

## Step 4: DNS

Add a CNAME record:
```
vpn.yourdomain.com.  CNAME  <gcore-provided-cname>.
```
Gcore shows the CNAME target after creating the resource.

---

## Step 5: Generate Client Configs

```python
from core.models import PhantomProvider, CdnRelay
from core.phantom import generate_cdn_uri

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

print("CDN proxy:", generate_cdn_uri(provider, relay_proxy))
print("Fronting:", generate_cdn_uri(provider, relay_front))
```

Or simply run the generator with `--mode cdn --cdn-domain ... [--fronting-sni ...]`
and copy the URIs from the `CLIENT URIS:` block.

---

## Step 6: Test CDN Fronting (optional)

Check whether Gcore allows SNI mismatch (true fronting). XHTTP issues an
HTTP/2 GET to the secret path; an authenticated request returns 200 and starts
streaming, an unauthenticated path returns the real website.

```bash
EDGE_IP=$(dig +short vpn.yourdomain.com | head -1)

# SNI = vk.com, Host = your CDN domain, path = secret → expect HTTP 200
curl -v --http2 --resolve "vk.com:443:$EDGE_IP" \
  -H "Host: vpn.yourdomain.com" \
  "https://vk.com/phantom/YOUR_TOKEN" 2>&1 | grep -E "< HTTP|alpn"

# 200 with SNI=vk.com,Host=your-domain → fronting works on this CDN.
# 421 Misdirected Request / 400 → fronting blocked; use CDN-as-proxy mode.
```

---

## CDN Fronting — Honest Assessment

| Mode | Reliability | Requirement |
|------|-------------|-------------|
| CDN-as-proxy | High — standard CDN usage | Domain on CDN, CDN IP whitelisted |
| True fronting | Unknown — CDN-dependent | CDN must not enforce SNI==Host |

Most large CDNs (Cloudflare, AWS) block true fronting. Gcore's free tier may or
may not. The subscription can include both URIs; the client tries both and uses
whichever connects.

---

## Alternative CDN Providers with Russian Presence

| Provider | Free tier | HTTP/2 | RU edge | Notes |
|----------|-----------|--------|---------|-------|
| Gcore | Yes | Yes | Moscow, SPb | Primary recommendation |
| EdgeCenter | Yes | Yes | Moscow | Gcore subsidiary |
| CDNVIDEO | No | ? | Moscow | Russian CDN, enterprise |
| VK Cloud CDN | No | ? | Moscow | Requires VK business account |
