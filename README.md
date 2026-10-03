# DM Internet Cafe: website, Wi-Fi voucher portal and dashboard

One Django project with three parts that share one database:

| Part | Address | Who uses it |
|------|---------|-------------|
| **Public website** | `/` | Anyone. Advertises services, Wi-Fi prices and contact details. |
| **Wi-Fi portal** | `/wifi/` | Customers. The page where they type their voucher code. |
| **Dashboard** (React) | `/dashboard/` | Owner and cashiers. Sell vouchers, print cards, see reports, change prices. |

Behind these are a REST API (`/api/`), the Django admin (`/admin/`) and the router connector
(`vouchers/router.py`).

**Stack:** Python 3.10+, Django 5, Django REST Framework, React 18 (Vite). SQLite by default,
PostgreSQL optional.

---

## 1. Run it on your computer

```bash
# in the project folder
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Mac / Linux

pip install -r requirements.txt
copy .env.example .env           # Windows   (Mac/Linux: cp .env.example .env)

python manage.py migrate
python manage.py createsuperuser     # this account is the OWNER
python manage.py runserver
```

Open:
- http://127.0.0.1:8000/ : the public website
- http://127.0.0.1:8000/dashboard/ : sign in with the owner account
- http://127.0.0.1:8000/wifi/ : the customer login page
- http://127.0.0.1:8000/admin/ : edit website text, services and staff accounts

The dashboard is already built, so you do **not** need Node.js just to run the project.

### Try the whole flow without a router
`ROUTER_MODE=mock` (the default in `.env.example`) pretends to be a router.
1. Sign in to the dashboard, open **Sell**, choose *1 Hour*, press **Sell**. A code appears.
2. Open `/wifi/`, type the code. You will see "Voucher accepted".
3. Open **Vouchers** and **Reports** to see it recorded.

### Run the automated tests
```bash
python manage.py test
```

---

## 2. Roles

- **Owner**: a user with *Staff status* ticked (the `createsuperuser` account has it). Sees everything:
  Sell, Vouchers, Print cards, Reports, Packages.
- **Cashier**: a normal user. Can only **Sell** and view **Vouchers**, and sees only their own sales.

Create a cashier: `/admin/` > Users > Add user. Leave *Staff status* **unticked**.

---

## 3. Things to change before the client sees it

1. **Contact details, opening hours, headline**: `/admin/` > *Website details*.
   The phone, email and address in the project are **placeholders**.
2. **Services list**: `/admin/` > *Services* (change text, order, hide any service).
   Your list includes *Computer Rental*. This system sells **Wi-Fi vouchers only**; it does not
   time computers. Hide that service if the cafe does not offer it.
3. **Packages and prices**: Dashboard > *Packages*. The starter prices ($1 / $2.50 / $5 / $20) are examples.
4. **Cafe name / currency**: `CAFE_NAME` and `CURRENCY_SYMBOL` in `.env`.
5. **Colours and fonts**: `website/static/website/site.css` (website), `portal/templates/portal/base.html`
   (login page), `frontend/src/styles.css` (dashboard).

---

## 4. How selling works

- **Quick sale (normal)**: cashier picks a package and how the customer paid. The system creates
  a code on the spot. Show it to the customer or print the slip.
- **Printed cards**: the owner makes a batch under *Print cards* and cuts them out. A card does
  **nothing until it is sold**: the cashier uses "Selling a card that is already printed?" and
  types the card's code. This stops anyone using stolen or unsold cards.
- The customer's time starts at **first login**, not at purchase. A sold voucher that is never used
  expires after the package's "must be used within" days (default 30).
- One voucher works on **one device** (the same device can reconnect).
- Reports are in the Africa/Harare timezone (`TIME_ZONE` in `config/settings.py`).

---

## 5. Editing the dashboard (React)

Needs Node.js 18+.
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (keep Django running on :8000)
npm run build      # writes into dashboard/static/dashboard/ so Django serves it
```
Source files: `frontend/src/App.jsx` and `frontend/src/pages/*.jsx`.

---

## 6. Connecting a real router

Set `ROUTER_MODE=mikrotik` and follow **`docs/MIKROTIK_SETUP.md`**. Read the section on how the
online server reaches the router first: it needs a VPN tunnel (or the server must sit inside the cafe).

---

## 7. Putting it online (checklist)

1. A Linux VPS or hosting with Python. Copy the project there and create a venv.
2. In `.env`: `DEBUG=0`, a long random `SECRET_KEY`, `ALLOWED_HOSTS=yourdomain.co.zw`,
   `CSRF_TRUSTED_ORIGINS=https://yourdomain.co.zw`, `ROUTER_MODE=mikrotik` plus the router settings.
   Optional: `DATABASE_URL=postgres://...` (and `pip install "psycopg[binary]"`).
3. `python manage.py migrate` then `python manage.py collectstatic --noinput`.
4. Run with `gunicorn config.wsgi --bind 127.0.0.1:8000 --workers 3` (use systemd to keep it running).
5. Put **HTTPS** in front (Caddy or nginx + Let's Encrypt). The portal and dashboard must not run on plain HTTP.
6. **Run the expiry job every minute** so finished vouchers are cut off:
   `* * * * * cd /path/to/project && /path/to/venv/bin/python manage.py expire_vouchers`
7. **Back up `db.sqlite3`** (or the PostgreSQL database) every day. It holds the cafe's sales records.

---

## 8. Not included (ideas for later)

- Automatic EcoCash/online payment: the `Sale` record already stores the payment method; a payment
  provider callback could call `sell_voucher` and show the code on screen.
- Timing and locking cafe computers (a separate piece of software on each PC).
- SMS/WhatsApp delivery of codes.

## Project layout

```
config/        settings, urls
vouchers/      models, selling/redeeming logic (services.py), router adapters (router.py), REST API (api.py), tests
portal/        the customer voucher page (templates are tiny and load nothing external)
website/       public site: models (Service, SiteInfo), template, CSS, starter content migration
dashboard/     serves the built React app at /dashboard/
frontend/      React source (Vite)
docs/          router setup guide
```
