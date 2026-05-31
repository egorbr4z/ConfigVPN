# PHANTOM XHTTP setup — the working recipe

Hard-won notes from getting XHTTP (network=`xhttp`) working behind nginx.
Read this before touching the transport.

## Topology

```
client → nginx :443 (TLS + HTTP/2) → Xray 127.0.0.1:10000 (xhttp, plaintext)
                ├─ /phantom/<token>  → Xray
                └─ everything else   → real website (anti-probe)
```

TLS is always terminated in front of Xray (nginx in direct mode, the CDN in
cdn mode). Xray never holds the cert and never binds a privileged port, so it
can run as the unprivileged `nobody` user.

## The five things that must be right

1. **Xray transport**: `network: "xhttp"`, `security: "none"`, listen
   `127.0.0.1:10000`. `xhttpSettings.path = /phantom/<token>`, `mode: "auto"`.

2. **nginx MUST enable HTTP/2** on the TLS listener:
   ```nginx
   listen 443 ssl;
   http2 on;
   ```
   XHTTP clients open an HTTP/2 connection. Without `http2 on;` nginx sees the
   HTTP/2 preface as garbage and logs `"PRI * HTTP/2.0" 400` for every request
   — the tunnel never establishes. This was the single biggest gotcha.

3. **Client URI must use `mode=packet-up`**:
   ```
   vless://<uuid>@<host>:443?encryption=none&security=tls&sni=<sni>&fp=chrome
        &type=xhttp&mode=packet-up&path=/phantom/<token>&host=<host>
   ```
   `mode=auto`/stream modes need HTTP/2 end-to-end *including* the nginx→Xray
   hop. nginx proxies to the backend over HTTP/1.1, which cannot carry a
   full-duplex stream, so stream modes fail with `read/write on closed pipe`.
   `packet-up` uses independent HTTP requests and survives the h2→h1.1 hop.

4. **nginx path location**: prefix match (XHTTP appends session sub-paths),
   buffering off both ways, HTTP/1.1 to backend, clear Connection header:
   ```nginx
   location /phantom/<token> {
       proxy_pass http://127.0.0.1:10000;
       proxy_http_version 1.1;
       proxy_set_header Host $host;
       proxy_set_header Connection "";
       proxy_buffering off;
       proxy_request_buffering off;
       client_max_body_size 0;
       proxy_read_timeout 300s;
   }
   ```

5. **Anti-probe fallback must avoid IPv6** if the host has no IPv6 route.
   `proxy_pass https://www.iana.org;` resolved an AAAA record → `connect()
   ... Network is unreachable`. Use a variable proxy_pass + resolver pinned to
   IPv4:
   ```nginx
   location / {
       resolver 1.1.1.1 8.8.8.8 ipv6=off valid=300s;
       set $phantom_fallback "www.iana.org";
       proxy_pass https://$phantom_fallback;
       proxy_ssl_server_name on;
       proxy_ssl_name www.iana.org;
       proxy_set_header Host www.iana.org;
   }
   ```

## Version requirements

- nginx ≥ 1.25.1 for `http2 on;`, ≥ 1.23.1 for `resolver ... ipv6=off`.
  (Both satisfied by Debian 13 / nginx 1.26.)
- Xray ≥ 24.11 for the `xhttp` transport (older builds call it `splithttp`).
- Client (v2rayTun / Happ / Hiddify / NekoBox) must be recent enough to parse
  `type=xhttp`.

## Quick verification

```bash
ss -tlnp | grep -E ':443|:10000'              # nginx:443, xray:10000
curl -sI --http2 https://<domain> | grep HTTP/2   # h2 negotiated
curl -sI https://<domain> | head -1               # 200 (anti-probe → real site)
tail -f /var/log/nginx/access.log                 # POST/GET /phantom/... → 200 (not "PRI * 400")
tail -f /var/log/xray/access.log                  # accepted ... [phantom-inbound -> direct]
```
