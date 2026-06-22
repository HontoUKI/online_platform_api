"""Тесты in-memory троттлинга входа."""
from app.api.endpoints import login


def setup_function():
    login.attempts_cache.clear()


def test_first_failed_attempt_starts_counter():
    login._track_failed_attempt("iin-1")
    assert login.attempts_cache["iin-1"]["count"] == 1


def test_lock_after_max_attempts():
    for _ in range(login.MAX_ATTEMPTS):
        login._track_failed_attempt("iin-2")
    entry = login.attempts_cache["iin-2"]
    assert entry["count"] == login.MAX_ATTEMPTS
    assert entry["unlock_at"] is not None
