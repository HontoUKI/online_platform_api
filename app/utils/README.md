# app/utils

Shared helpers used across the API layer.

- `auth.py` — password hashing (passlib/bcrypt), JWT creation/decoding, and the role
  dependencies injected into routers: `get_current_user`, `get_current_admin_user`,
  `get_current_teacher_user`, `get_current_student_user`. Requires `SECRET_KEY` (raises on
  import if unset).
- `access.py` — helper checks for whether a user may see a given module/subject, keeping
  authorization logic out of the routers.
- `startup_utils.py` — `ensure_admin_exists`, used by [../startup.py](../startup.py) to create
  the bootstrap admin when configured.
