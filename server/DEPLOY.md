# PHANTOM — развёртывание с нуля

Пошаговая инструкция по поднятию PHANTOM на голых серверах.

PHANTOM работает в двух режимах, которые сосуществуют на одном exit-сервере:

| Режим | Против чего | Как клиент входит |
|-------|-------------|-------------------|
| **direct**    | блэклист / DPI (ТСПУ) | напрямую на домен exit-сервера |
| **whitelist** | белые списки          | через домашний (РФ) relay по raw TCP |

Архитектура:

```
                    ┌──────────────────── direct ───────────────────┐
клиент ──TLS──────────────────────────────────────► exit :443 (nginx)
                                                       ├─ /phantom/<token> → Xray :10000 (xhttp)
клиент ──TLS──► RF relay :443 ──raw TCP──► exit :443   └─ всё прочее → реальный сайт (anti-probe)
                    └─────────────── whitelist ──────────────────────┘
```

TLS всегда end-to-end между клиентом и exit-сервером. Relay слепой — он не
расшифровывает трафик и не хранит сертификат.

---

## 0. Что нужно заранее

**Серверы:**
- **Exit** (зарубежный): VPS на Debian 12/13 или Ubuntu 22.04+, root-доступ,
  публичный IPv4, минимум 1 vCPU / 1 GB RAM.
- **Relay** (РФ, опционально — только для обхода белых списков): тоже Debian/Ubuntu,
  root, публичный IPv4. Российский хостинг (его IP с большей вероятностью проходит).

**Домен:**
- Домен или поддомен, указывающий **A-записью на IP exit-сервера**.
  Например `vpn.example.com → 1.2.3.4`. DNS должен прорезолвиться до запуска
  (certbot проверяет владение доменом).

**Порты на exit:** 22 (SSH), 80 (Let's Encrypt), 443 (PHANTOM).
**Порты на relay:** 22, 443.

---

## 1. Exit-сервер (зарубежный)

### 1.1. Подготовка

```bash
# залогиньтесь как root на exit-сервере
apt update && apt install -y git
git clone https://github.com/egorbr4z/configvpn.git /opt/phantom
cd /opt/phantom
```

Убедитесь, что домен резолвится на этот сервер:

```bash
dig +short vpn.example.com     # должен вернуть IP этого сервера
```

Если пусто или другой IP — сначала поправьте DNS и дождитесь распространения.

### 1.2. Установка

```bash
IP=$(curl -s4 ifconfig.me)
sudo bash server/install_exit.sh --domain vpn.example.com --ip "$IP"
```

Скрипт сам:
1. поставит nginx, certbot, Xray;
2. получит Let's Encrypt сертификат;
3. сгенерирует конфиги и применит их (`--apply`);
4. выдаст права Xray на чтение сертификата и запись логов;
5. включит и запустит nginx + xray;
6. напечатает VLESS-ссылки.

**Сохраните вывод** — там VLESS URI и master secret. Secret также лежит в
`/etc/phantom/phantom.secret` — это ключ ко всем подключениям, не теряйте его.

Полезные опции:

```bash
# свой secret + 3 юзера + сразу прописать relay
sudo bash server/install_exit.sh \
    --domain vpn.example.com --ip "$IP" \
    --secret "ваш-секрет" --users 3 --relay-ip 185.10.20.30
```

### 1.3. Проверка

```bash
ss -tlnp | grep -E ':443|:10000'                 # nginx :443, xray :10000
curl -sI --http2 https://vpn.example.com | head -2   # HTTP/2 200
curl -sI https://vpn.example.com | head -1           # 200 — отдаётся реальный сайт (anti-probe)
```

Anti-probe-проверка: запрос к корню `/` должен вернуть **реальный сайт**
(не 404, не пустую страницу). Это маскирует сервер под обычный веб-сайт.

### 1.4. Подключение клиента (direct)

Возьмите ссылку `PHANTOM-Direct` из вывода и импортируйте в клиент
(v2rayTun / Happ / Hiddify / NekoBox). Подключитесь — это direct-режим против DPI.

На этом для обхода блэклиста/DPI всё готово. Дальше — только если нужен обход
**белых списков**.

---

## 2. Relay-сервер (РФ) — только для обхода белых списков

### 2.1. Подготовка

```bash
# залогиньтесь как root на РФ-сервере
apt update && apt install -y git
git clone https://github.com/egorbr4z/configvpn.git /opt/phantom
cd /opt/phantom
```

### 2.2. Установка

```bash
sudo bash server/install_relay.sh \
    --exit-ip 1.2.3.4 \
    --exit-domain vpn.example.com \
    --secret "ваш-секрет"      # тот же secret, что на exit — чтобы скрипт напечатал URI
```

`--secret` опционален: без него relay поднимется так же, просто не напечатает
готовую `PHANTOM-Whitelist` ссылку (её всё равно можно взять с exit-сервера).

Скрипт:
1. поставит nginx + stream-модуль;
2. напишет `stream {}` passthrough-конфиг на exit;
3. включит его в `nginx.conf` (верхний уровень, рядом с `http{}`);
4. откроет порт 443;
5. запустит nginx и проверит `nc -z exit:443`.

### 2.3. Привязать relay к exit

Relay только пересылает TCP. Чтобы клиент получил ссылку с адресом relay,
**на exit-сервере** перегенерируйте конфиги с IP relay:

```bash
# на EXIT-сервере
RELAY_IP=185.10.20.30
sudo python3 server/generate_config.py \
    --domain vpn.example.com --ip 1.2.3.4 \
    --secret "ваш-секрет" \
    --relay-ip "$RELAY_IP" --apply
```

В выводе появится ссылка `PHANTOM-Whitelist` (адрес = IP relay, SNI = домен exit).

> Это не меняет работу exit-сервера — direct продолжает работать. Просто
> добавляется второй вход.

### 2.4. Проверка relay

```bash
# на relay: видит ли он exit
nc -vz 1.2.3.4 443

# с клиента: relay прозрачно отдаёт сертификат exit
curl -sI --resolve vpn.example.com:443:185.10.20.30 https://vpn.example.com | head -1   # 200
```

### 2.5. Подключение клиента (whitelist)

Импортируйте ссылку `PHANTOM-Whitelist` в клиент. Можно держать **обе** ссылки
(direct + whitelist) — клиент подключится по той, что проходит.

---

## 3. Тест белого списка (на Linux-клиенте)

Перед реальным ограничением можно сымитировать белый список — пустить трафик
только на IP relay:

```bash
sudo ./server/whitelist_sim.sh on 185.10.20.30/32
#   → direct-ссылка (IP exit) не подключается
#   → whitelist-ссылка (IP relay) работает
sudo ./server/whitelist_sim.sh off
```

---

## 4. Обслуживание

**Добавить пользователей** — перегенерировать с `--users N` и перезапустить Xray:

```bash
sudo python3 server/generate_config.py --domain vpn.example.com --ip 1.2.3.4 \
    --secret "ваш-секрет" --users 5 --apply
sudo systemctl restart xray
```

**Обновление сертификата** — certbot ставит таймер автоматически. Проверка:

```bash
certbot renew --dry-run
```

После реального обновления перезапустите Xray (он держит cert в памяти):

```bash
sudo systemctl restart xray
```

**Логи и диагностика:**

```bash
journalctl -xeu xray            # ошибки Xray
journalctl -xeu nginx           # ошибки nginx
tail /var/log/nginx/access.log  # запросы; "PRI * HTTP/2.0" 400 = нет http2 on (см. XHTTP_SETUP.md)
tail /var/log/xray/access.log   # accepted ... [phantom-inbound -> direct] = туннель работает
nginx -t                        # проверка конфига nginx
xray run -test -config /usr/local/etc/xray/config.json   # проверка конфига Xray
```

---

## 5. Частые проблемы

| Симптом | Причина | Решение |
|---------|---------|---------|
| certbot падает | DNS не указывает на сервер / порт 80 закрыт | проверьте `dig`, откройте :80 |
| Xray не стартует: `permission denied` на cert | Xray запущен не от root | скрипт ставит `User=root` в systemd drop-in; проверьте `cat /etc/systemd/system/xray.service.d/20-user.conf` |
| `"PRI * HTTP/2.0" 400` в access.log | нет `http2 on;` на :443 | проверьте `nginx_fallback.conf`, перегенерируйте |
| `read/write on closed pipe` | клиент в режиме `mode=auto`/stream | URI должен быть `mode=packet-up` (генератор уже так делает) |
| anti-probe отдаёт 404 вместо сайта | сломан fallback / нет IPv4-резолвера | см. `server/configs/XHTTP_SETUP.md` п.5 |
| relay не видит exit (`nc` fails) | фаервол exit или relay | откройте :443 на обоих, проверьте маршрут |

Подробности по транспорту XHTTP — в `server/configs/XHTTP_SETUP.md`.
Подробности по relay — в `server/configs/whitelist_relay.md`.
