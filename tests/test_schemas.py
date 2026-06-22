"""Тесты Pydantic-схем."""
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
