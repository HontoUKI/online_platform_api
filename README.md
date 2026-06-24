# Online Platform API

Backend for an educational online platform: authentication, role-based access (admin /
teacher / student), modules, subjects, lessons, tests and grades.

Built with FastAPI and async SQLAlchemy on PostgreSQL.

## Current Scope

- JWT authentication with login throttling (5 attempts, 5-minute lock).
- Three roles with dependency-based guards: admin, teacher, student.
- Admin management: users, groups (incl. Excel import), modules and subjects.
- Access control: linking groups to modules and teachers to subjects.
- Lessons (video / pdf / test), homework upload and grading.
- Tests with questions, options and results.
- Student grade summary across submissions and tests.
- Static file serving for uploaded photos and lesson documents.

## Tech stack

- FastAPI + Starlette
- SQLAlchemy 2 (async) + asyncpg (PostgreSQL)
- Alembic (migrations)
- PyJWT + passlib/bcrypt
- pandas + openpyxl (Excel group import)
- Uvicorn / Gunicorn

## Run

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create a local `.env` from the example and fill in real values:

```powershell
Copy-Item .env.example .env
```

`SECRET_KEY` is required — the app refuses to start without it.

Create the PostgreSQL database, then apply migrations:

```powershell
alembic upgrade head
```

Start the development server:

```powershell
uvicorn app.main:app --reload
```

Production (example):

```powershell
gunicorn app.main:app -k uvicorn.workers.UvicornWorker
```

## Environment variables

See [.env.example](.env.example). Key variables:

- `DATABASE_URL` — PostgreSQL async URL (`postgresql+asyncpg://...`). Alembic converts the
  driver to `psycopg2` automatically.
- `SECRET_KEY` — required; long random string for JWT signing.
- `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` — JWT settings.
- `PLACE_URL` — comma-separated allowed CORS origins. If empty, CORS is open but credentials
  are disabled.
- `ADMIN_IIN`, `ADMIN_PASSWORD`, `ADMIN_FULL_NAME`, `ADMIN_PHONE` — bootstrap admin. If IIN or
  password is missing, no admin is created.

Never commit the real `.env`. Only `.env.example` is tracked.

## Tests

Unit tests (no database required) live in `tests/` and run with pytest:

```powershell
pip install -r requirements-dev.txt
pytest
```

They cover password hashing/JWT ([tests/test_auth.py](tests/test_auth.py)), Pydantic schemas
and the login throttle. The Alembic migration is exercised end-to-end in CI against a real
PostgreSQL service.

## Load testing

A [Locust](https://locust.io) scenario lives in [loadtest/locustfile.py](loadtest/locustfile.py):
each virtual user logs in once and then loops authenticated reads (`/access/my-modules`,
`/lessons/student/grades`, `/auth/check`). It is a manual tool — run it against a running
instance, not in CI.

Start the API, then point Locust at it (credentials come from the environment):

```powershell
$env:LOAD_TEST_IIN = "000000000000"
$env:LOAD_TEST_PASSWORD = "<password>"
locust -f loadtest/locustfile.py --host http://localhost:8000
```

Open http://localhost:8089 for the web UI, or run headless:

```powershell
locust -f loadtest/locustfile.py --host http://localhost:8000 --headless -u 50 -r 5 -t 1m
```

Notes:

- **Test a production-like target, not the dev server.** `uvicorn --reload` is a single worker
  and will start refusing connections under load (`ConnectionRefusedError`), which measures the
  dev server collapsing rather than the API. Use multiple workers:
  - Local (incl. Windows): `uvicorn app.main:app --workers 4` (no `--reload`).
  - Production (Linux): `gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4`
    (`gunicorn` does not run on Windows).
- **Login is CPU-bound (bcrypt)**, so it dominates latency and serializes on a single worker.
  The scenario logs in once per user (`on_start`) to isolate read throughput.
- **Mind the DB pool vs. `max_connections`.** Each worker keeps its own pool of up to
  `DB_POOL_SIZE + DB_MAX_OVERFLOW` connections (defaults 5 + 10 = 15). With `N` workers the total
  is `N × 15`, which **must stay under Postgres `max_connections`** (default 100) — otherwise
  excess requests get `500 too many connections`. A 4-worker / `10+20` pool (120 > 100) was the
  cause of the `500`s seen in load testing; the defaults are now conservative and tunable via env.
  `DB_POOL_TIMEOUT` makes a request wait for a free connection (queue) instead of failing fast.
  To scale beyond `max_connections`, raise it or put PgBouncer in front. Ramp users gradually
  (`-r`) to find the knee.

## Security

- **SQL injection:** all database access goes through the SQLAlchemy ORM
  (`select().where(...)`), so values are sent as bound parameters — never string-formatted into
  SQL. There is no raw SQL, no `text()`, and `order_by` uses fixed model columns only (no
  user-controlled identifiers). Parameterization is covered by
  [tests/test_sql_injection.py](tests/test_sql_injection.py).
- **Auth:** JWT (HS256) with a required `SECRET_KEY`; role guards per endpoint; passwords hashed
  with bcrypt; login throttling.
- **File downloads:** JWT-gated and resolved strictly inside `static/` (no path traversal); only
  `static/photos` is served publicly. See [tests/test_files.py](tests/test_files.py).
- **File uploads:** server-generated filenames (never the client's — closes an arbitrary-write
  hole), size limits, and type allowlists; avatars are images only (no SVG → no inline XSS).
  See [app/utils/uploads.py](app/utils/uploads.py) and [tests/test_uploads.py](tests/test_uploads.py).
- **Input validation:** IIN is constrained to 12 digits at the schema layer, so malformed or
  injection-shaped values are rejected (422) before any query.
- **Response headers:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, a restrictive `Content-Security-Policy`, and `Strict-Transport-Security`
  (HSTS) on HTTPS requests only (skipped on plain-http localhost).
- **No dangerous sinks:** no `eval`/`exec`, `subprocess`, `pickle` or `yaml.load`.

## CI

[.github/workflows/ci.yml](.github/workflows/ci.yml) runs on every push to `main` and on pull
requests: installs deps, runs pytest, then applies `alembic upgrade head` against a throwaway
PostgreSQL 16 service to verify migrations.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — layers and project shape.
- [docs/API.md](docs/API.md) — request paths (all routes, methods and required roles).

## Notes

The interactive API docs (`/docs`, `/redoc`, `/openapi.json`) are disabled by default in
[app/main.py](app/main.py). Database tables are auto-created on startup as a development
convenience; production should rely on `alembic upgrade head` (see ARCHITECTURE → Decisions
To Revisit).
