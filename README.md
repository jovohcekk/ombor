# Ombor — Inventory Management System

Django inventory platform for warehouses, shops, and small businesses. The primary interface is a **custom dashboard** at `/dashboard/`; Django’s built-in admin is available at `/manage/`.

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

Python 3.12, Django 6.1, Django REST Framework, SimpleJWT, PostgreSQL (production), SQLite (local), WhiteNoise, Gunicorn, Bootstrap 5, Chart.js

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
| `EMAIL_HOST`, `EMAIL_PORT` | SMTP server used for admin password reset |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Optional SMTP authentication credentials |
| `EMAIL_USE_TLS`, `EMAIL_USE_SSL` | SMTP transport security; enable only one |
| `DEFAULT_FROM_EMAIL` | Sender address for password reset messages |

## Database setup

- Local: leave `DATABASE_URL` empty → SQLite file `db.sqlite3`
- Production: set `DATABASE_URL` to PostgreSQL (Render injects this automatically)

## Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

## Superuser and password resets

```bash
python manage.py createsuperuser
```

The built-in admin is at `/manage/`. Its password reset link uses the configured SMTP
server. In local development, reset messages are written to the console. Production
requires `EMAIL_HOST` and `DEFAULT_FROM_EMAIL`; configure SMTP credentials in the
hosting environment rather than in source control.

### One-time production superuser password reset

`reset_superuser_password_once` is a temporary, explicit management command. It accepts
the username and new password only through environment variables, refuses non-PostgreSQL
databases, checks the expected PostgreSQL host and database name, and changes only the
password of an existing superuser. It validates and verifies the new password without
printing it. It is not part of application startup, deployment, or an HTTP endpoint.

Do not add this command to `build.sh`, the Render build/start commands, or a recurring
job. Run it once from a Render one-off command facility only if that facility is
available for the service and plan and supports transient environment variables for
that invocation (not saved service settings). This repository's Render web service is
configured on the `free` plan; if the dashboard does not offer that capability, use the
authorized local method below rather than changing the service start command.

#### Run once from an authorized local Windows machine

Use the PostgreSQL **external** connection string and its matching host shown in the
Render database dashboard. The machine must be authorized to connect; if the database
uses IP allowlisting, temporarily allow the machine's public IP and remove that access
immediately afterward. Do not use the internal Render connection string from outside
Render, and do not paste a connection string or password into a command argument,
source file, `.env`, or chat.

From the repository root in PowerShell, activate the project's virtual environment,
then run this interaction. Secure prompts prevent credentials from being echoed or
stored in shell history. The password and database URL are placed in process-scoped
environment variables only because Django reads its configuration from the environment.
`DEBUG=True` is set only for this local process so production-only SMTP settings are not
needed; the command still requires PostgreSQL and the exact expected database host/name.

```powershell
function Set-ProcessSecretFromPrompt {
    param([string]$Name, [string]$Prompt)
    $secureValue = Read-Host -Prompt $Prompt -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue)
    try {
        [Environment]::SetEnvironmentVariable(
            $Name,
            [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr),
            'Process'
        )
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        $secureValue.Dispose()
    }
}

try {
    $env:DEBUG = 'True'
    $env:OMBOR_RESET_SUPERUSER_USERNAME = Read-Host 'Existing superuser username'
    $env:OMBOR_RESET_SUPERUSER_EXPECTED_DB_NAME = Read-Host 'Expected production database name'
    $env:OMBOR_RESET_SUPERUSER_EXPECTED_DB_HOST = Read-Host 'Expected production database host'
    $env:OMBOR_RESET_SUPERUSER_CONFIRM_PRODUCTION = 'I_UNDERSTAND_THIS_CHANGES_A_PRODUCTION_PASSWORD'
    Set-ProcessSecretFromPrompt 'DATABASE_URL' 'Render external PostgreSQL connection string'
    Set-ProcessSecretFromPrompt 'OMBOR_RESET_SUPERUSER_PASSWORD' 'New superuser password'
    python manage.py reset_superuser_password_once
    if ($LASTEXITCODE -ne 0) {
        throw "Password reset command failed with exit code $LASTEXITCODE."
    }
}
finally {
    Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:\OMBOR_RESET_SUPERUSER_USERNAME -ErrorAction SilentlyContinue
    Remove-Item Env:\OMBOR_RESET_SUPERUSER_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:\OMBOR_RESET_SUPERUSER_CONFIRM_PRODUCTION -ErrorAction SilentlyContinue
    Remove-Item Env:\OMBOR_RESET_SUPERUSER_EXPECTED_DB_HOST -ErrorAction SilentlyContinue
    Remove-Item Env:\OMBOR_RESET_SUPERUSER_EXPECTED_DB_NAME -ErrorAction SilentlyContinue
    Remove-Item Env:\DEBUG -ErrorAction SilentlyContinue
    Remove-Item Function:\Set-ProcessSecretFromPrompt -ErrorAction SilentlyContinue
}
```

Only treat the reset as successful if the command reports that it reset and verified the
password. Afterward, verify the new credentials by logging in through the normal admin
login. Then delete
`apps/accounts/management/commands/reset_superuser_password_once.py` and its now-empty
`management` package directories from the source tree, remove the temporary command
tests, and deploy that removal. Also remove any temporary Render IP allowlist entry and
close the local PowerShell session to clear its process environment. Never save the
temporary credentials in Render environment variables or repository files.

Seed sample data only in a local or disposable staging database:

```bash
python manage.py seed_data
```

The seed command creates its sample accounts with unusable passwords and never changes
passwords of existing accounts. Set an account password explicitly with Django's
`changepassword` command when needed. Do not run sample-data commands against production.

## Run development server

```bash
python manage.py runserver
```

- Login: http://127.0.0.1:8000/login/
- Register: http://127.0.0.1:8000/register/
- Dashboard: http://127.0.0.1:8000/dashboard/
- Django admin: http://127.0.0.1:8000/manage/
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
  -d "{\"username\":\"YOUR_USERNAME\",\"password\":\"YOUR_PASSWORD\"}"
```

## Render deployment

1. Create a Blueprint from `render.yaml`, or a Web Service + PostgreSQL database.
2. Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` for the deployed hostname. When
   `RENDER_EXTERNAL_HOSTNAME` is present, settings also add the Render hostname and
   its HTTPS origin automatically.
3. Configure `EMAIL_HOST` and `DEFAULT_FROM_EMAIL`; add SMTP username/password if
   required by the provider. Keep credentials in Render environment variables.
4. `build.sh` installs dependencies, collects static files, and applies pending
   migrations. Review migration operations before deploying schema changes.
5. Start command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 60`

If `RENDER_EXTERNAL_HOSTNAME` is present, it is added to `ALLOWED_HOSTS` and CSRF origins automatically.

### Media files in production

Product images are stored in `MEDIA_ROOT`. Render’s disk is ephemeral, so uploads disappear on redeploy. For a sellable production install, point `STORAGES["default"]` at S3-compatible storage (`django-storages` + bucket credentials via environment variables).

## Production configuration

- `DEBUG=False`
- Strong unique `SECRET_KEY` (Render generates one from the Blueprint)
- PostgreSQL via `DATABASE_URL`
- HTTPS cookies and HSTS when `DEBUG=False`
- SMTP configuration for password reset
- External object storage for media
- Never use sample-data accounts as production credentials

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
| PDF export returns 501 | PDF generation is not implemented; CSV export is available |
