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
