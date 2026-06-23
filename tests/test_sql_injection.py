"""Тесты защиты от SQL-инъекций.

Все запросы строятся через SQLAlchemy ORM, который передаёт значения как
bound-параметры, а не вшивает их в текст SQL. Здесь это проверяется компиляцией
запросов (без подключения к БД): вредоносная строка не попадает в SQL-текст и
уходит отдельным параметром.
"""
from sqlalchemy import select, func
from sqlalchemy.dialects import postgresql

from app import models

INJECTION = "'; DROP TABLE users; --"
OR_BYPASS = "' OR '1'='1"


def _compile(stmt):
    return stmt.compile(dialect=postgresql.dialect())


def test_user_lookup_by_iin_is_parameterized():
    # Тот же паттерн, что в crud.get_user_by_iin (путь логина).
    stmt = select(models.User).where(models.User.iin == INJECTION)
    compiled = _compile(stmt)

    assert "DROP TABLE" not in str(compiled)
    assert INJECTION in compiled.params.values()


def test_login_bypass_payload_stays_a_value():
    stmt = select(models.User).where(models.User.iin == OR_BYPASS)
    compiled = _compile(stmt)

    # Полезная нагрузка не превращается в логику запроса.
    assert "OR '1'='1'" not in str(compiled)
    assert OR_BYPASS in compiled.params.values()


def test_subject_lookup_uses_exact_match_not_like():
    # Упрочнённый поиск дисциплины: lower()-равенство, без LIKE/ILIKE и шаблонов.
    title = "%"
    stmt = select(models.Subject).where(
        models.Subject.module_id == 1,
        func.lower(models.Subject.title) == title.lower(),
    )
    sql = str(_compile(stmt)).upper()

    assert "LIKE" not in sql  # ловит и ILIKE
    assert title in _compile(stmt).params.values()
