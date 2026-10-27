# Ombor — Inventory Management System

Production-ready Django inventory platform for warehouses, shops, and small businesses. The primary interface is a **custom admin dashboard** at `/dashboard/`. Django’s built-in `/admin/` is not used as the product UI.

## Features

- Product and category CRUD with images, unique SKU, purchase/selling prices, and stock levels
- Stock IN, OUT, and ADJUSTMENT with atomic transactions and movement history
- Dashboard statistics, charts, notifications, and low-stock alerts
- Reports with date filters, CSV export, and a PDF service hook
- Custom users with Super Admin, Manager, and Staff roles (enforced on the server)
- Public registration with validated, unique username/email and Django password hashing
- REST API with JWT, pagination, search, filtering, and OpenAPI docs at `/api/docs/`
- Render.com deployment (Gunicorn, WhiteNoise, PostgreSQL)

## Technologies

Python 3.12, Django 5, Django REST Framework, SimpleJWT, PostgreSQL (production), SQLite (local), WhiteNoise, Gunicorn, Bootstrap 5, Chart.js

## Project structure

```
ombor/
├── config/                 # Django project (settings, URLs, WSGI/ASGI)
├── apps/
│   ├── accounts/           # Custom user, roles, JWT, permissions
│   ├── products/           # Category and Product models + API
│   ├── inventory/          # StockMovement and stock services
│   ├── dashboard/          # Custom panel views, forms, seed command
│   └── reports/            # CSV/PDF report services
├── templates/
├── static/
├── media/
├── manage.py
├── requirements.txt
├── .env.example
├── build.sh
└── render.yaml
```

## Installation

```bash
cd ombor
python -m venv env
# Windows
env\Scripts\activate
# macOS/Linux
source env/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Do not treat `env/` as application source. It is the virtual environment.

## Environment variables

See `.env.example`. Never commit `.env`.

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Django secret (required in production) |
| `DEBUG` | `True` locally, `False` in production |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `DATABASE_URL` | Empty for SQLite; Postgres URL in production |
| `CSRF_TRUSTED_ORIGINS` | Full origins, e.g. `https://your-app.onrender.com` |
| `CORS_ALLOWED_ORIGINS` | Optional API browser origins |
| `SECURE_SSL_REDIRECT` | HTTPS redirect when `DEBUG=False` |
| `TIME_ZONE` | Default `Asia/Tashkent` |

## Database setup

- Local: leave `DATABASE_URL` empty → SQLite file `db.sqlite3`
- Production: set `DATABASE_URL` to PostgreSQL (Render injects this automatically)

## Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

## Superuser

```bash
python manage.py createsuperuser
```

Or demo data (local / staging only):

```bash
python manage.py seed_data
```

Demo accounts (change immediately; they are **not** created automatically in production):

| User | Password | Role |
|------|----------|------|
| `admin` | `Admin123!` | Super Admin |
| `manager` | `Demo12345!` | Manager |
| `staff` | `Demo12345!` | Staff |

## Run development server

```bash
python manage.py runserver
```

- Login: http://127.0.0.1:8000/login/
- Register: http://127.0.0.1:8000/register/
- Dashboard: http://127.0.0.1:8000/dashboard/
- API docs: http://127.0.0.1:8000/api/docs/

## Roles

| Role | Access |
|------|--------|
| Super Admin | All dashboard pages and `/api/users/` |
| Manager | Products, categories, stock, reports |
| Staff | Product view, stock IN/OUT, stock history |

Inactive users cannot log in. Permissions are checked in views and API classes, not only in the UI.

New users can register at `/register/`. Registration creates a Staff account in the
configured Django database, applies Django's password validators and password hashing,
and starts a session. Username and email uniqueness is case-insensitive and enforced
both in registration validation and by database constraints. Local accounts are stored
in `db.sqlite3`; deployments use the configured `DATABASE_URL` (the Render Blueprint
provisions PostgreSQL). Account persistence across deployments depends on that database
being retained by the hosting provider.

## API documentation

Interactive schema: `/api/docs/`

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/token/` | JWT obtain (username or email) |
| `POST /api/auth/token/refresh/` | JWT refresh |
| `/api/products/` | Products (write: manager+) |
| `/api/categories/` | Categories (manager+) |
| `/api/stock/` | Movement list |
| `POST /api/stock/in/` | Stock in |
| `POST /api/stock/out/` | Stock out |
| `POST /api/stock/adjust/` | Adjustment |
| `/api/users/` | Users (super admin) |

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"Admin123!\"}"
```

## Render deployment

1. Push this repository (exclude `.env` and `env/`).
2. Create a Blueprint from `render.yaml`, or a Web Service + PostgreSQL database.
3. Set `ALLOWED_HOSTS` to your Render hostname.
4. Set `CSRF_TRUSTED_ORIGINS` to `https://<your-host>`.
5. `build.sh` installs dependencies, collects static files, and migrates.
6. Start command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

If `RENDER_EXTERNAL_HOSTNAME` is present, it is added to `ALLOWED_HOSTS` and CSRF origins automatically.

### Media files in production

Product images are stored in `MEDIA_ROOT`. Render’s disk is ephemeral, so uploads disappear on redeploy. For a sellable production install, point `STORAGES["default"]` at S3-compatible storage (`django-storages` + bucket credentials via environment variables).

## Production configuration

- `DEBUG=False`
- Strong unique `SECRET_KEY`
- PostgreSQL via `DATABASE_URL`
- HTTPS cookies and HSTS when `DEBUG=False`
- External object storage for media
- Do not rely on `seed_data` passwords

## Tests and checks

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py migrate
python manage.py test
python manage.py collectstatic --noinput
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Static files 404 in production | Confirm `collectstatic` ran; WhiteNoise is enabled |
| CSRF error on Render | Add `https://your-app.onrender.com` to `CSRF_TRUSTED_ORIGINS` |
| Login fails for a user | Confirm `is_active` and password |
| Permission denied | Check `role` (super_admin / manager / staff) |
| Insufficient stock | OUT quantity is greater than on-hand stock |
| PDF export returns 501 | Expected until WeasyPrint/ReportLab is wired in `apps/reports/pdf.py` |
