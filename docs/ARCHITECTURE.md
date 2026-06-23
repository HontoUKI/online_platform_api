# Architecture

## Background

The project started as an MVP built under tight deadlines, so the first version favoured
shipping working features over polish. Some traces of that remain (and are being cleaned up
incrementally): occasional over-verbose comments, a few naming inconsistencies, and the
auto-create-tables fallback on startup. The notes in "Decisions To Revisit" track what's left.

## Shape

The backend is a single FastAPI application assembled in [app/main.py](../app/main.py),
which wires routers, CORS and a startup hook (`lifespan`).

```text
app/
  main.py        App factory: routers, CORS, static mount, lifespan startup
  database.py    Async engine, session factory, Base, get_async_db dependency
  models.py      SQLAlchemy ORM models and the UserRole enum
  schemas.py     Pydantic request/response schemas
  crud.py        Database operations (the data-access layer)
  startup.py     On-startup: create tables + ensure bootstrap admin
  api/           HTTP layer (routers)
  utils/         Auth, access checks and startup helpers
migrations/      Alembic environment and versioned migrations
static/          Served uploads (photos, lesson documents)
tests/           pytest unit tests (auth, schemas, login throttle)
```

## Layers

Requests flow **router → crud → models**:

- **`api/`** holds the HTTP layer only — request parsing, role guards and response shaping.
  See [app/api/README.md](../app/api/README.md).
- **`crud.py`** is the single place that talks to the database. Routers call CRUD functions;
  they do not build queries inline. Relationships are eager-loaded with `selectin` to stay
  safe under async sessions.
- **`models.py` / `schemas.py`** are kept separate: ORM models vs. the Pydantic shapes that
  cross the API boundary. `UserRole` exists in both — compare roles against the enum, not raw
  strings.

## Auth

[app/utils/auth.py](../app/utils/auth.py) issues and validates JWTs and exposes the role
dependencies: `get_current_user`, `get_current_admin_user`, `get_current_teacher_user`,
`get_current_student_user`. `SECRET_KEY` is mandatory; the module raises on import if it is
missing. Login throttling lives in [app/api/endpoints/login.py](../app/api/endpoints/login.py)
as an in-memory cache.

## Database & migrations

The app uses an async engine (`asyncpg`). Alembic runs synchronously, so
[migrations/env.py](../migrations/env.py) reads `DATABASE_URL` and swaps `+asyncpg` for
`+psycopg2`. `target_metadata` is bound to `Base.metadata`, so autogenerate sees all models.

```powershell
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Decisions To Revisit

- **Drop `create_all` on startup.** [startup.py](../app/startup.py) still creates tables for
  development convenience; production should rely solely on Alembic migrations.
- **Move login throttling to Redis.** The current `attempts_cache` is in-memory: it resets on
  restart and is not shared across workers.
- **Refresh tokens.** Access tokens expire (default 30 min) with no refresh flow yet.
- **Timezone-aware timestamps.** Submission/result timestamps and model defaults still use
  naive `datetime.utcnow`; migrate to timezone-aware values consistently.
