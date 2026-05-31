# PHANTOM — развёртывание с нуля

Пошаговая инструкция по поднятию PHANTOM на голых серверах.

PHANTOM использует транспорт **VLESS + Vision + REALITY**: exit-серверу **не
нужен домен и сертификат** — Xray слушает :443 напрямую и заимствует TLS-рукопожатие
реального сайта (по умолчанию `www.microsoft.com`). Для ТСПУ/DPI соединение
неотличимо от обычного захода на этот сайт. Неаутентифицированные пробы
прозрачно проксируются на тот же сайт (встроенный anti-probe).

Два режима входа сосуществуют:

| Режим | Против чего | Как клиент входит |
|-------|-------------|-------------------|
| **direct**    | блэклист / DPI (ТСПУ) | напрямую на IP exit-сервера |
| **whitelist** | белые списки          | через домашний (РФ) relay по raw TCP |

Архитектура:

```
                    ┌──────────────── direct ────────────────┐
клиент ──REALITY/TLS─────────────────────────► exit :443 (Xray, REALITY)
                                                  ├─ аутентиф. клиент → туннель
клиент ──REALITY──► RF relay :443 ──raw TCP──►    └─ проба/DPI → www.microsoft.com
                    └────────────── whitelist ──────────────┘
```

REALITY-рукопожатие всегда end-to-end между клиентом и exit. Relay слепой — он
пересылает сырой TCP, ничего не расшифровывает и не хранит ключей.

> **XHTTP-режим** (старый, через nginx+домен+cert) остаётся доступен через
> `--transport xhttp`. Он нужен только если ваши клиенты не умеют REALITY
> (почти все умеют) или для CDN-сценариев. См. раздел 5.

---

## 0. Что нужно заранее

**Серверы:**
- **Exit** (зарубежный): VPS на Debian 12/13 или Ubuntu 22.04+, root, публичный
  IPv4, минимум 1 vCPU / 1 GB RAM.
- **Relay** (РФ, опционально — только для обхода белых списков): тоже Debian/Ubuntu,
  root, публичный IPv4. Российский хостинг (его IP с большей вероятностью проходит).

**Домен:** для REALITY **не нужен**. (Нужен только для `--transport xhttp`.)

**Порты на exit:** 22 (SSH), 443 (PHANTOM).
**Порты на relay:** 22, 443.

---

## 1. Exit-сервер (зарубежный) — REALITY

### 1.1. Подготовка

```bash
# залогиньтесь как root на exit-сервере
apt update && apt install -y git
git clone https://github.com/egorbr4z/configvpn.git /opt/phantom
cd /opt/phantom
```

### 1.2. Установка

```bash
IP=$(curl -s4 ifconfig.me)
sudo bash server/install_exit.sh --ip "$IP"
```

Скрипт:
1. поставит Xray (официальный установщик);
2. сгенерирует x25519-ключи REALITY (`xray x25519`);
3. сгенерирует и применит конфиг (`generate_config.py --transport reality --apply`);
4. настроит Xray на запуск от root и слушание :443;
5. откроет фаервол, запустит и включит xray;
6. напечатает VLESS-ссылки.

**Сохраните вывод** — там VLESS URI и ключи. Они также в `/etc/phantom/phantom.secret`.

Полезные опции:

```bash
# другой "донор" рукопожатия + 3 юзера + сразу relay
sudo bash server/install_exit.sh --ip "$IP" \
    --reality-sni www.cloudflare.com --reality-dest www.cloudflare.com:443 \
    --users 3 --relay-ip 185.10.20.30
```

> **Про выбор `--reality-sni`/`--reality-dest`:** сайт-донор должен быть
> доступен из РФ, поддерживать TLS 1.3 + HTTP/2 + X25519 и сам не быть
> заблокированным. Хорошие варианты: `www.microsoft.com`, `www.cloudflare.com`,
> `dl.google.com`, `www.apple.com`. SNI и dest должны указывать на один сайт.

### 1.3. Проверка

```bash
ss -tlnp | grep :443        # Xray слушает :443
systemctl status xray       # active (running)
journalctl -u xray -n 30    # без ошибок REALITY
```

Проверка «маскировки»: запрос по IP сервера должен увидеть **сертификат
сайта-донора** (например microsoft.com), а не ошибку:

```bash
echo | openssl s_client -connect $IP:443 -servername www.microsoft.com 2>/dev/null \
    | openssl x509 -noout -subject   # subject = реальный сайт-донор
```

### 1.4. Подключение клиента (direct)

Возьмите ссылку `PHANTOM-Reality` из вывода и импортируйте в клиент
(v2rayTun / Happ / Hiddify / NekoBox / sing-box). Это direct-режим против DPI.

Для обхода блэклиста/DPI на этом всё. Дальше — только если нужен обход
**белых списков**.

---

## 2. Relay-сервер (РФ) — только для обхода белых списков

Relay — слепой TCP-passthrough на :443 → exit:443. С REALITY рукопожатие идёт
end-to-end сквозь relay, ничего расшифровывать не нужно.

### 2.1. Подготовка

```bash
# залогиньтесь как root на РФ-сервере
apt update && apt install -y git
git clone https://github.com/egorbr4z/configvpn.git /opt/phantom
cd /opt/phantom
```

### 2.2. Установка

```bash
sudo bash server/install_relay.sh --exit-ip 1.2.3.4
```

Скрипт ставит nginx + stream-модуль, пишет passthrough-конфиг на exit:443,
включает его в `nginx.conf`, открывает :443 и проверяет `nc -z exit:443`.

> `--exit-domain` для REALITY не обязателен (он был нужен только для печати
> старого xhttp-URI).

### 2.3. Привязать relay к exit

**На exit-сервере** перегенерируйте конфиг с IP relay, **переиспользуя уже
сгенерированные ключи** — добавится ссылка `PHANTOM-Reality-Whitelist`:

```bash
# на EXIT-сервере
source /etc/phantom/phantom.secret
sudo python3 /opt/phantom/server/generate_config.py \
    --ip 1.2.3.4 --transport reality \
    --reality-sni "$REALITY_SNI" --reality-dest "$REALITY_DEST" \
    --reality-private-key "$REALITY_PRIVATE_KEY" \
    --reality-public-key  "$REALITY_PUBLIC_KEY" \
    --reality-short-id    "$REALITY_SHORT_ID" \
    --relay-ip 185.10.20.30 --apply
sudo systemctl restart xray
```

Direct-режим продолжает работать — просто добавляется второй вход.

### 2.4. Проверка relay

```bash
# на relay: видит ли он exit
nc -vz 1.2.3.4 443

# с клиента: relay прозрачно отдаёт рукопожатие донора
echo | openssl s_client -connect <RELAY_IP>:443 -servername www.microsoft.com 2>/dev/null \
    | openssl x509 -noout -subject
```

### 2.5. Подключение клиента (whitelist)

Импортируйте `PHANTOM-Reality-Whitelist`. Можно держать обе ссылки (direct +
whitelist) — клиент подключится по той, что проходит.

---

## 3. Тест белого списка (на Linux-клиенте)

```bash
sudo ./server/whitelist_sim.sh on 185.10.20.30/32
#   → direct-ссылка (IP exit) не подключается
#   → whitelist-ссылка (IP relay) работает
sudo ./server/whitelist_sim.sh off
```

---

## 4. Обслуживание

**Добавить пользователей** — перегенерировать с `--users N` (переиспользуя ключи
из `/etc/phantom/phantom.secret`, как в 2.3) и перезапустить Xray.

**Скорость.** Включите BBR на exit (и relay) — на трансграничном канале это
часто кратно поднимает throughput:
```bash
cat >> /etc/sysctl.conf <<'EOF'
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
EOF
sysctl -p && sysctl net.ipv4.tcp_congestion_control   # → bbr
```

**Логи и диагностика:**
```bash
journalctl -xeu xray            # ошибки Xray
tail /var/log/xray/access.log   # accepted ... [phantom-reality -> direct]
xray run -test -config /usr/local/etc/xray/config.json   # проверка конфига
```

---

## 5. XHTTP-режим (опционально, нужен домен)

Если нужен старый транспорт за nginx (клиент без REALITY, CDN-сценарий):

```bash
# DNS: vpn.example.com → IP exit-сервера (A-запись) ДО запуска
sudo bash server/install_exit.sh --transport xhttp \
    --ip "$IP" --domain vpn.example.com
```

Этот путь ставит nginx + certbot, получает Let's Encrypt cert и поднимает
XHTTP за nginx. Детали транспорта — `server/configs/XHTTP_SETUP.md`.

---

## 6. Частые проблемы

| Симптом | Причина | Решение |
|---------|---------|---------|
| Xray не стартует | битый конфиг | `xray run -test -config /usr/local/etc/xray/config.json` |
| `permission denied` на логах/cert | Xray запущен не от root | drop-in `User=root` (скрипт ставит); `cat /etc/systemd/system/xray.service.d/20-user.conf` |
| Клиент не коннектится | не совпали ключи/sid/sni | сверьте `pbk`/`sid`/`sni` в URI с `/etc/phantom/phantom.secret` |
| Подключается, но рвётся | донор REALITY недоступен/блокируется из РФ | смените `--reality-sni`/`--reality-dest` на другой живой сайт |
| Низкая скорость при хорошем пинге | нет BBR | включите BBR (раздел 4) |
| relay не видит exit (`nc` fails) | фаервол | откройте :443 на обоих |

Подробности по relay — `server/configs/whitelist_relay.md`.
