# app/api/admin_endpoints

Admin-only routers. Every endpoint depends on `get_current_admin_user` (one teacher-level
exception in `modules.py`). Mounted under `/admin/*` in [../../main.py](../../main.py).

- `users.py` — `/admin/users`: create, list, delete users and reset passwords.
- `groups.py` — `/admin/groups`: create/list groups, manage membership, Excel import, and
  group deletion (with or without members).
- `modules.py` — `/admin/modules`: create/list/update/delete modules and add subjects.

See [../../../docs/API.md](../../../docs/API.md) for the full method/path table.
