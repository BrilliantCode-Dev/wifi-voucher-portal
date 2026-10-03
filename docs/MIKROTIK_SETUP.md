# Connecting the system to a MikroTik router

Commands are for **RouterOS v7**. Menus differ slightly between versions, so test every step on a
spare router (or MikroTik's free virtual router, "CHR") before the cafe's real one.

## How the pieces talk

```
Customer phone --Wi-Fi--> MikroTik hotspot --(redirect)--> https://yourdomain/wifi/  (portal page)
                                   ^                                  |
                                   |  creates a timed user (API)      |
                                   +------ VPN tunnel <---------------+  Django server
```

1. A customer connects. The hotspot blocks the internet and sends their browser to your portal page,
   passing their device address (MAC) and the router's login link.
2. They type a voucher code. Django checks it and tells the router "allow this device for N minutes".
3. Django's reply makes the customer's browser sign in to the router, and the internet opens.
4. Every minute `manage.py expire_vouchers` removes finished vouchers from the router.

## Important: how an online server reaches the router

Django must connect **to the router's API** (port 8728). Most cafe routers sit behind the
internet provider's NAT, so the internet cannot connect in, and you should never expose the API
port publicly anyway. Two safe options:

- **A. WireGuard tunnel (recommended for an online server).** The router connects *out* to your
  server and creates a private link (below). Django then uses the router's tunnel address.
- **B. Run Django inside the cafe** on a small always-on mini PC connected to the router. No tunnel
  is needed (`ROUTER_HOST` = the router's LAN IP). The public website can then be hosted separately.

### Option A: WireGuard

On the Linux server (`apt install wireguard`), create `/etc/wireguard/wg0.conf`:
```
[Interface]
Address = 10.99.0.1/24
ListenPort = 51820
PrivateKey = <server private key: wg genkey>

[Peer]
PublicKey = <router public key, from step below>
AllowedIPs = 10.99.0.2/32
```
Open UDP 51820 on the server firewall, then `systemctl enable --now wg-quick@wg0`.

On the router (RouterOS v7):
```
/interface wireguard add name=wg-dm listen-port=13231
/interface wireguard print                      # copy the router's public-key into wg0.conf above
/ip address add address=10.99.0.2/24 interface=wg-dm
/interface wireguard peers add interface=wg-dm public-key="<SERVER PUBLIC KEY>" \
    endpoint-address=<SERVER PUBLIC IP> endpoint-port=51820 \
    allowed-address=10.99.0.1/32 persistent-keepalive=25s
```
Test: from the server `ping 10.99.0.2`. Then in `.env`: `ROUTER_HOST=10.99.0.2`.

## Step 1: Hotspot

Run the wizard on the Wi-Fi/bridge interface customers use:
```
/ip hotspot setup
```
Note the hotspot address it uses (often `10.5.50.1` or `192.168.88.1`). Put it in `.env`:
`HOTSPOT_LOGIN_HOSTS=10.5.50.1`. The portal only sends customers back to addresses listed there.

Allow plain-password login (our page signs the customer in automatically):
```
/ip hotspot profile print                       # note your profile name
/ip hotspot profile set <profile-name> login-by=http-pap
```

## Step 2: API account for Django

```
/user group add name=portal-api policy=api,read,write
/user add name=portal group=portal-api password=<LONG RANDOM PASSWORD> address=10.99.0.1
/ip service set api disabled=no address=10.99.0.1/32
/ip firewall filter add chain=input protocol=tcp dst-port=8728 src-address=10.99.0.1 action=accept \
    comment="DM portal API" place-before=0
```
In `.env`: `ROUTER_MODE=mikrotik`, `ROUTER_USER=portal`, `ROUTER_PASSWORD=<same password>`, `ROUTER_PORT=8728`.
(If Django runs inside the cafe, use the LAN address instead of `10.99.0.1`/`10.99.0.2`.)

## Step 3: Let customers reach the portal before they log in ("walled garden")

```
/ip hotspot walled-garden add dst-host=yourdomain.co.zw action=allow
/ip hotspot walled-garden ip add dst-address=<SERVER PUBLIC IP> action=accept
```
The first line covers web names; the second is needed because the portal is HTTPS.

## Step 4: Send customers to the portal

In WinBox: **Files** > `hotspot/login.html`. Replace its whole content with:
```html
<html><head>
<meta http-equiv="refresh" content="0; url=https://yourdomain.co.zw/wifi/?mac=$(mac)&ip=$(ip)&login=$(link-login-only)&dst=$(link-orig-esc)">
</head><body></body></html>
```
The `$(...)` parts are filled in by the router. If your RouterOS version rejects any of them,
check MikroTik's "Hotspot customisation" page for the exact variable names.

## Step 5: Test, in this order

1. `ping 10.99.0.2` works from the server (tunnel up).
2. On the server: `python manage.py shell`, then
   ```python
   from vouchers.router import get_router
   r = get_router(); r.add_user("TEST-0001", 5, "AA:BB:CC:DD:EE:FF"); r.remove_user("TEST-0001")
   ```
   No error means the API link works. Check `/ip hotspot user print` on the router in between.
3. Connect a phone to the Wi-Fi: the portal page should open by itself.
4. Sell a voucher in the dashboard, type the code on the phone: internet opens.
5. A second phone using the same code is refused.
6. Wait for the time to run out (try a short test package): the phone is cut off after the
   `expire_vouchers` job runs.

## Common problems

- **Portal page does not open**: walled garden entries missing, or `login.html` not replaced.
- **"We could not connect you right now"**: Django cannot reach the router API. Check the tunnel,
  the API user/password and the firewall rule. Details are in the server log.
- **Customer sent to the router but not signed in**: `login-by=http-pap` not set, or the router's
  address is missing from `HOTSPOT_LOGIN_HOSTS`.
- **Time seems to run out early/late**: Django ends a voucher at *first login + package time* on the
  clock; the router also counts connected time. Whichever finishes first applies.
