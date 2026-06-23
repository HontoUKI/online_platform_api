# API — Request Paths

All routes, grouped by router prefix (see [app/main.py](../app/main.py)). Access column:
**public**, **auth** (any logged-in user), **student**, **teacher** (teacher or admin) or
**admin**. Interactive docs are disabled, so this file is the route reference.

Base URL: the server root. All paths below include their router prefix.

## `/auth` — Authentication

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST | `/auth/login` | public | Log in by IIN + password; returns token and user. Throttled. |
| POST | `/auth/token` | public | OAuth2 password flow token endpoint. |
| GET  | `/auth/check` | auth | Validate the current token. |

## `/user` — Current user

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| GET   | `/user/by-iin/{iin}` | auth | Look up a user by IIN. |
| POST  | `/user/update-phone` | auth | Update own phone. |
| POST  | `/user/upload-photo` | auth | Upload own avatar (multipart). |
| PATCH | `/user/change-password` | auth | Change own password. |

## `/admin/users` — User management (admin)

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST   | `/admin/users/` | admin | Create a user. |
| GET    | `/admin/users/` | admin | List users. |
| DELETE | `/admin/users/{iin}` | admin | Delete a user. |
| PATCH  | `/admin/users/reset_password` | admin | Reset a user's password. |

## `/admin/groups` — Group management (admin)

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST   | `/admin/groups/` | admin | Create a group. |
| GET    | `/admin/groups/` | admin | List groups. |
| GET    | `/admin/groups/{group_id}` | admin | Get a group. |
| POST   | `/admin/groups/{group_id}/users` | admin | Add users to a group. |
| GET    | `/admin/groups/{group_id}/users` | admin | List group members. |
| DELETE | `/admin/groups/{group_id}/users/{user_id}` | admin | Remove a user from a group. |
| POST   | `/admin/groups/upload-excel` | admin | Import a group + users from Excel (multipart). |
| DELETE | `/admin/groups/{group_id}` | admin | Delete a group (keep users). |
| DELETE | `/admin/groups/{group_id}/with-users` | admin | Delete a group with its users. |

## `/admin/modules` — Module management

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST   | `/admin/modules/` | admin | Create a module. |
| GET    | `/admin/modules/` | auth | List modules. |
| GET    | `/admin/modules/with-teachers` | admin | List modules with their teachers. |
| GET    | `/admin/modules/{module_id}` | auth | Get a module. |
| PUT    | `/admin/modules/{module_id}` | admin | Update a module. |
| DELETE | `/admin/modules/{module_id}` | admin | Delete a module. |
| POST   | `/admin/modules/{module_id}/subjects` | admin | Add a subject to a module. |
| DELETE | `/admin/modules/subjects/{subject_id}` | teacher | Delete a subject. |

## `/access` — Access control

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| GET    | `/access/access-overview` | admin | Overview of group/module/subject access. |
| POST   | `/access/admin/group-to-module` | admin | Grant a group access to a module. |
| POST   | `/access/admin/teacher-to-subject` | admin | Assign a teacher to a subject. |
| GET    | `/access/module/{module_id}/groups` | admin | Groups linked to a module. |
| GET    | `/access/admin-modules` | admin | All modules (admin view). |
| GET    | `/access/admin-modules/{module_id}` | admin | One module (admin view). |
| GET    | `/access/my-modules` | auth | Modules available to the current user. |
| GET    | `/access/my-modules/{module_id}` | auth | One available module with details. |
| GET    | `/access/teacher-modules` | teacher | Modules the teacher teaches. |
| GET    | `/access/teacher-modules/{module_id}` | teacher | One teacher module. |
| GET    | `/access/teacher-subjects` | teacher | Subjects the teacher teaches. |
| GET    | `/access/subjects/{subject_id}/lessons` | auth | Lessons of a subject. |
| POST   | `/access/subjects/{subject_id}/groups/{group_id}` | admin | Link a group to a subject. |
| DELETE | `/access/subjects/{subject_id}/groups/{group_id}` | admin | Unlink a group from a subject. |
| GET    | `/access/lessons/{lesson_id}` | auth | Full lesson with access check. |

## `/lessons` — Lessons, homework and grades

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST   | `/lessons/add/subjects/{subject_id}` | teacher | Add a lesson to a subject. |
| GET    | `/lessons/{lesson_id}` | auth | Get a lesson. |
| DELETE | `/lessons/{lesson_id}` | teacher | Delete a lesson. |
| POST   | `/lessons/upload/lesson-file` | teacher | Upload a lesson file (multipart). |
| POST   | `/lessons/{lesson_id}/submit-homework` | auth | Submit homework: up to 5 files (`files`, multipart) and/or a comment. |
| GET    | `/lessons/{lesson_id}/my-submissions` | auth | Current user's submissions for a lesson. |
| GET    | `/lessons/{lesson_id}/submissions/files` | teacher | All file submissions for a lesson. |
| GET    | `/lessons/{lesson_id}/submissions/tests` | teacher | All test results for a lesson. |
| DELETE | `/lessons/submission/{submission_id}` | auth | Delete a submission. |
| DELETE | `/lessons/result/{result_id}` | teacher | Delete a test result. |
| PATCH  | `/lessons/submission/{submission_id}/grade` | teacher | Grade a submission. |
| GET    | `/lessons/student/grades` | auth | Grade summary for the current student. |

## `/tests` — Tests

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST   | `/tests/create` | auth | Create a test with questions. |
| GET    | `/tests/{test_id}` | auth | Get a full test. |
| GET    | `/tests/by-subject/{subject_id}` | auth | List tests of a subject. |
| PUT    | `/tests/{test_id}` | auth | Update a test. |
| DELETE | `/tests/{test_id}` | auth | Delete a test (204). |
| POST   | `/tests/submit` | auth | Submit answers; returns a result. |

## `/files` — File download

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| GET | `/files/download/{file_path:path}` | auth | Download a stored file. Requires JWT; the path is resolved strictly inside `static/` (no traversal). |

Public avatars are served separately via the `/static/photos` mount. Lesson materials and
homework uploads are reachable **only** through this authenticated endpoint.
