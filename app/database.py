import os
import logging
import asyncio
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем строку подключения к базе данных
DATABASE_URL = os.getenv("DATABASE_URL")

# Проверка на наличие строки подключения
if DATABASE_URL is None:
    logging.error("DATABASE_URL is not set in the environment variables.")
    exit(1)

# Создание асинхронного движка SQLAlchemy
engine = create_async_engine(
    DATABASE_URL,
    echo=True,         # Установить True для вывода SQL-запросов в консоль (отладка)
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"connect_timeout": 10},
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
