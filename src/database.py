"""Модуль управления асинхронным подключением к базе данных PostgreSQL.

Инициализирует асинхронный движок SQLAlchemy, настраивает фабрику сессий
и предоставляет генератор изолированных сессий для обработки HTTP-запросов
в рамках веб-приложения FastAPI.
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/twitter_db",
)

engine = create_async_engine(DATABASE_URL, echo=True)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Базовый декларативный класс для всех ORM-моделей приложения.

    Используется в качестве метаданных для автоматической генерации таблиц
    и связывания моделей с таблицами в базе данных PostgreSQL.
    """


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Генератор изолированных асинхронных сессий базы данных (Dependency Injection).

    Обеспечивает создание новой сессии для каждого входящего HTTP-запроса,
    гарантирует автоматическое закрытие сессии и освобождение ресурсов
    после завершения обработки запроса или при возникновении ошибок.

    Yields:
        AsyncSession: Изолированная асинхронная сессия SQLAlchemy для работы с БД.
    """
    async with async_session_factory() as session:
        yield session
