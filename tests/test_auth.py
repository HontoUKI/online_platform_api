"""Юнит-тесты хеширования паролей и JWT (без БД)."""
import jwt
import pytest

from app.utils import auth


def test_password_hash_roundtrip():
    hashed = auth.get_password_hash("s3cret")
    assert hashed != "s3cret"
    assert auth.verify_password("s3cret", hashed) is True
    assert auth.verify_password("wrong", hashed) is False


def test_access_token_contains_subject_and_expiry():
    token = auth.create_access_token({"sub": "123456789012"})
    payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    assert payload["sub"] == "123456789012"
    assert "exp" in payload


def test_access_token_rejects_wrong_secret():
    token = auth.create_access_token({"sub": "x"})
    with pytest.raises(jwt.InvalidTokenError):
        jwt.decode(token, "wrong-secret", algorithms=[auth.ALGORITHM])
