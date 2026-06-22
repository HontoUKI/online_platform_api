# app/api

The HTTP layer. Each module defines a FastAPI `APIRouter` that is mounted with a prefix in
[../main.py](../main.py). Routers parse requests, enforce role guards (from
[../utils/auth.py](../utils/auth.py)) and shape responses; all database work is delegated to
[../crud.py](../crud.py).

Full route reference: [../../docs/API.md](../../docs/API.md).

## endpoints/

User-facing routers:

- `login.py` — `/auth`: login, OAuth2 token, token check, login throttling.
- `user.py` — `/user`: own profile (phone, photo, password) and IIN lookup.
- `access.py` — `/access`: module/subject access for admins, teachers and students.
- `lessons.py` — `/lessons`: lessons, homework submission, grading, grade summary.
- `tests.py` — `/tests`: tests, questions and result submission.
- `files.py` — `/files`: file download.

## admin_endpoints/

Admin-only management routers — see [admin_endpoints/README.md](admin_endpoints/README.md).
