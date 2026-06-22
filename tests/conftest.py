"""Общая настройка тестов.

Выставляем переменные окружения ДО импорта модулей приложения: `database.py`
завершает процесс без DATABASE_URL, а `auth.py` падает без SECRET_KEY. Движок БД
создаётся лениво (без подключения), поэтому фиктивного URL достаточно для импорта.
"""
import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test_db",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")
os.environ.setdefault("ALGORITHM", "HS256")
