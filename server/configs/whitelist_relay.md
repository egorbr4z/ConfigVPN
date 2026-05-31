# PHANTOM whitelist entry — domestic TCP relay

The realistic way to survive a leaky/regional whitelist: enter through a
**domestic server** whose IP is reachable (domestic hosting often still passes
even when foreign IPs are dropped), and relay to the foreign exit.

```
client (restricted) → RF relay :443 (domestic IP, passes) ──raw TCP──> exit kav22.ru:443 → Xray → internet
```

## Why a relay and not a CDN

- **Foreign CDNs (Gcore, Cloudflare) don't help under a whitelist** — their IPs
  are foreign and/or unreachable in the region, so they fail the "reachable +
  whitelisted" test. (See gcore_setup.md only for blacklist/DPI scenarios.)
- A **Russian CDN** would work but needs KYC and *terminates your TLS*, i.e. it
  can inspect/log — a trust compromise.
- A **TCP-passthrough relay** forwards raw TLS: it never decrypts, needs no
  cert, and TLS stays end-to-end with the exit. The relay is dumb and blind.

## Two modes, one exit

Both client URIs hit the **same exit** (same UUID, secret path, cert). Only the
entry address differs:

| Mode | Client connects to | SNI / Host | Use when |
|------|--------------------|------------|----------|
| direct    | exit domain (`kav22.ru`) | `kav22.ru` | normal / DPI-blacklist |
| whitelist | relay IP                 | `kav22.ru` | exit IP blocked, domestic IP passes |

The client can hold both and fall back to whichever connects.

## Exit server (kav22.ru)

No changes — keep the working direct XHTTP setup. It already serves the secret
path → Xray and a real site for everything else.

## Relay server (domestic)

1. Generate the relay config (run anywhere; `--ip` is the EXIT's public IP):
   ```bash
   python3 server/generate_config.py --domain kav22.ru --ip <EXIT_IP> \
       --secret "$SECRET" --mode direct --relay-ip <RELAY_IP>
   ```
   This emits a `PHANTOM-Whitelist` client URI plus `relay_stream.conf`.

2. On the relay:
   ```bash
   apt install -y nginx libnginx-mod-stream
   cp relay_stream.conf /etc/nginx/phantom-relay.conf
   # include it at the TOP LEVEL of nginx.conf (sibling of http{}, NOT inside it):
   echo 'include /etc/nginx/phantom-relay.conf;' >> /etc/nginx/nginx.conf
   ufw allow 443/tcp
   nginx -t && systemctl reload nginx
   ```
   Nothing else runs on the relay's :443 — it is pure passthrough.

3. Point the client at the `PHANTOM-Whitelist` URI (address = relay IP).

## Verify

```bash
# from the relay: it should reach the exit
nc -vz <EXIT_IP> 443

# from a client: relay presents the exit's cert (passthrough)
curl -sI --resolve kav22.ru:443:<RELAY_IP> https://kav22.ru | head -1   # 200

# whitelist simulation (Linux client): allow only the relay IP
sudo ./server/whitelist_sim.sh on <RELAY_IP>/32
#   → direct URI (exit IP) fails, whitelist URI (relay IP) connects
sudo ./server/whitelist_sim.sh off
```

## Caveats

- The relay→exit hop crosses the border; datacenters usually have unrestricted
  international transit, so this holds even when the client's mobile link is
  whitelisted. Confirm the relay can reach the exit (`nc -vz`).
- "Domestic IP passes" is an empirical bet that depends on the region and the
  moment — test during an actual restriction. It is not guaranteed.
