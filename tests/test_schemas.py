"""Тесты Pydantic-схем."""
import pytest
from pydantic import ValidationError

from app import schemas


def test_user_short_name_builds_initials():
    user = schemas.User(iin="123456789012", full_name="Иванов Иван Иванович", id=1)
    assert user.short_name == "Иванов И. И."


def test_user_short_name_single_word():
    user = schemas.User(iin="123456789012", full_name="Админ", id=1)
    assert user.short_name == "Админ"


def test_user_model_validate_from_attributes():
    class FakeORM:
        iin = "123456789012"
        full_name = "Петров Пётр"
        phone = None
        role = "student"
        id = 7
        photo = None

    user = schemas.User.model_validate(FakeORM())
    assert user.id == 7
    assert user.short_name == "Петров П."


def test_login_accepts_valid_iin():
    req = schemas.LoginRequest(iin="123456789012", password="secret")
    assert req.iin == "123456789012"


@pytest.mark.parametrize(
    "bad_iin",
    ["12345", "12345678901a", "' OR '1'='1", "", "1234567890123"],
)
def test_login_rejects_malformed_iin(bad_iin):
    with pytest.raises(ValidationError):
        schemas.LoginRequest(iin=bad_iin, password="secret")
