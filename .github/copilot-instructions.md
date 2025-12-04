## Quick orientation

This repository is a small Django REST-style API (no DRF) implementing a home-banking proof-of-concept.

- Project root: top-level `manage` and `README.md` are under `demo_project/`.
- Django settings: `demo_project/demo_project/settings.py` (DB is configured for PostgreSQL: host `host.docker.internal`).
- App module: `demo_project/api_app/` contains `views.py`, `models.py`, `urls.py`, `tests.py`, and migrations in `demo_project/api_app/migrations/`.

## Big-picture architecture

- Single Django project with one app `api_app`. The URL prefix is configured in `demo_project/demo_project/urls.py` as `path('api/', include('api_app.urls'))`.
- All endpoints are function-based views in `api_app/views.py` (no Django REST Framework). JSON is returned via `JsonResponse` and request bodies are parsed using `json.loads(request.body)`.
- Geocoding: `geopy.Nominatim` is used in `views.create_user` and `views.update_user` to derive `latitude`/`longitude` from an address.
- Data layer: simple Django models with `to_json()` helpers in `api_app/models.py`. Key model details:
  - `Client` stores `name`, `address`, `birthdate`, `latitude`, `longitude`.
  - `Account` stores `balance` (DecimalField), `number` (unique), `account_type` and FK to `Client`.

## Project-specific patterns and notable behaviors

- No DRF: HTTP handling is manual. Look for `JsonResponse`, manual status codes, and `csrf_exempt` on mutating endpoints.
- Input validation pattern: the helper `get_input_property_or_error(data, prop)` is used to raise a ValueError when a required property is missing. Many endpoints wrap logic in broad try/except and return JSON with a `message` key and an HTTP status code (400, 404, 503, etc.).
- Geocoding calls are synchronous and call `nominatim.geocode(address).raw`; failures return 503 responses.
- Monetary transfers use `decimal.Decimal` and update `Account.balance` directly; there is no explicit DB transaction or locking in the code (be cautious when modifying transfer behavior).
- Account uniqueness: `Account.number` is unique; `create_account` prevents duplicates by checking existing accounts before creating.

## How to run & developer workflows (Windows PowerShell examples)

- Activate the virtualenv (created in this repository):

  .\Scripts\Activate.ps1

- Run Django development server (from repo root):

  python demo_project\manage.py runserver

- Apply migrations / create DB objects:

  python demo_project\manage.py migrate

- Run tests (app-level):

  python demo_project\manage.py test api_app

Notes: settings.py points to a Postgres DB at `host.docker.internal:5432` (database name `poc`, user `postgres`, password `admin`). For local dev without Postgres, you can temporarily switch `DATABASES['default']` to use SQLite in `demo_project/demo_project/settings.py`.

## Common endpoints (examples)

- List users (GET): `/api/users`
- Create user (POST): `/api/users/create/` with body (JSON):

  {
    "name": "Doe",
    "birthdate": "01-01-1980",
    "address": "10 Downing St, London"
  }

- Update user (PUT): `/api/users/<id>/update/` (JSON body similar to create)
- List accounts (GET): `/api/accounts`
- Create account (POST): `/api/users/<user_id>/account/create/` (JSON with `account_type` and `number`)
- Transfer between accounts (PATCH): `/api/accounts/transfer/` with body:

  {
    "src_account": "1234567890123456",
    "dest_account": "6543210987654321",
    "amount": 10.50
  }

## Where to look first when editing code

- `demo_project/demo_project/settings.py` — DB and installed apps.
- `demo_project/api_app/views.py` — main business logic, geocoding, error handling patterns.
- `demo_project/api_app/models.py` — data shapes and `to_json()` helpers.
- `demo_project/api_app/urls.py` — endpoint routing (quick overview of available endpoints).

## Safety and gotchas discovered in the code

- Broad exceptions: many `except:` blocks catch all exceptions. When changing logic, prefer catching specific exceptions to avoid hiding issues.
- No explicit DB transaction on transfers: concurrent requests may cause race conditions. If you implement concurrency-safe transfers, add Django `transaction.atomic()` blocks and appropriate SELECT ... FOR UPDATE semantics.
- Geocoding external dependency: `geopy` calls are live HTTP calls; tests or offline runs should mock `geopy.Nominatim` or switch to a stub.

## Quick examples for code edits

- To add a new GET endpoint: add a function in `views.py`, register it in `api_app/urls.py` and follow the project pattern of returning `JsonResponse` with `message` on errors.
- When adding model fields, update migration files under `demo_project/api_app/migrations/` by running `python demo_project\manage.py makemigrations api_app` then `migrate`.

If anything is unclear or you want the instructions to emphasize other workflows (docker, CI, or local Postgres setup), tell me what to add and I will iterate.
