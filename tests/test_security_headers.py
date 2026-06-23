"""Проверка, что ответы несут заголовки безопасности."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_security_headers_present_on_response():
    resp = client.get("/")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in resp.headers["Content-Security-Policy"]
