"""Тесты безопасности отдачи файлов: требуется JWT и нет path traversal."""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.api.endpoints import files

# TestClient без `with` не запускает lifespan (нет подключения к БД);
# для проверки 401 этого достаточно — токен отбрасывается до обращения к БД.
client = TestClient(app)


def test_download_requires_jwt():
    resp = client.get("/files/download/photos/whatever.jpg")
    assert resp.status_code == 401


def test_resolve_static_path_blocks_traversal():
    for evil in ["../requirements.txt", "../../.env", "../app/database.py"]:
        with pytest.raises(HTTPException) as exc:
            files.resolve_static_path(evil)
        assert exc.value.status_code == 403


def test_resolve_static_path_allows_paths_inside_static():
    resolved = files.resolve_static_path("lesson_docs/file.pdf")
    assert resolved.startswith(files.STATIC_ROOT)
