# Marketplace Stock Dashboard

A small Django portfolio MVP for practicing database-backed web development and marketplace API integration. The dashboard combines recent Ozon FBS order lines, the latest Ozon stock balances, and stock quantities entered for a seller's own warehouses.

## Features

- Read recent FBS postings and product stock balances from Ozon Seller API.
- Store imported order lines and the latest stock balances in SQLite.
- Add or update own-warehouse stock by warehouse name and seller SKU.
- Compare available quantities from Ozon and own warehouses on one page.
- Keep Ozon credentials in a local `.env` file instead of storing or displaying them in the application.
- Use Django's built-in authentication; create the local dashboard user through Django's management command.

## Requirements

- Python 3.10 or newer.
- Ozon Seller API Client ID and API key for live synchronization. The application can also be explored locally without credentials; synchronization remains disabled until they are configured.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` locally. Set `DJANGO_SECRET_KEY` to a private random value, then fill in `OZON_CLIENT_ID` and `OZON_API_KEY` if you want to test live synchronization. Never commit `.env` or paste marketplace credentials into source code.

Create the local database and dashboard account:

```bash
python manage.py migrate
python manage.py createsuperuser
```

Start the local server and open `http://127.0.0.1:8000/`:

```bash
python manage.py runserver
```

Log in with the account created above. Add own-warehouse quantities in the dashboard. If Ozon credentials are configured, use **Загрузить заказы и остатки** to request data from Ozon.

## Configuration

The project reads these values from `.env`:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django signing key. Use a private random value. |
| `DJANGO_DEBUG` | Enables debug mode for local development; defaults to `true`. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed host names. |
| `OZON_CLIENT_ID` | Ozon Seller API Client ID. |
| `OZON_API_KEY` | Ozon Seller API key with read permissions for orders and stock information. |

The default database is a project-local SQLite file named `db.sqlite3`. The previous external MySQL database is not configured or contacted.

## Tests

```bash
python manage.py test
```

API tests use mocked responses and do not contact Ozon or require real credentials.

## MVP limits

- The integration is read-only and covers Ozon only. It does not change stock in a marketplace account.
- The current stock endpoint groups balances by Ozon fulfillment type (FBO/FBS), not by each named warehouse.
- Own-warehouse balances are entered manually.
- The dashboard stores the latest stock state; it does not retain a historical stock timeline.
- Wildberries, automatic cross-marketplace stock synchronization, multiple companies in one installation, and public deployment are outside this MVP.
- Ozon API permissions, account data, and response formats can affect live synchronization. Tests validate application behavior against representative mocked responses, not a live seller account.
