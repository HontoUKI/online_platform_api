import os
import logging
import asyncio
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем строку подключения к базе данных
DATABASE_URL = os.getenv("DATABASE_URL")

# Проверка на наличие строки подключения
if DATABASE_URL is None:
    logging.error("DATABASE_URL не выставлен в переменный окружения")
    exit(1)

# Размер пула на ОДИН процесс-воркер. Важно: при N воркерах суммарно открывается
# до N * (POOL_SIZE + MAX_OVERFLOW) соединений — это число должно укладываться в
# postgres max_connections (по умолчанию 100), иначе под нагрузкой часть запросов
# получит 500 («too many connections»). Поэтому дефолты консервативные и настраиваются.
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # ждать свободное соединение, сек

# Создание асинхронного движка SQLAlchemy
engine = create_async_engine(
    DATABASE_URL,
    echo=False,         # Установить True для вывода SQL-запросов в консоль (отладка)
    pool_pre_ping=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    connect_args={"timeout": 10},  # asyncpg: тайм-аут установки соединения, сек
)

# Базовый класс для всех моделей
Base = declarative_base()

# Асинхронная сессия — используется в Depends
async_session = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# Получение асинхронной сессии из Depends
async def get_async_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

# (Опционально) Создание всех таблиц — используется только в разработке
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
