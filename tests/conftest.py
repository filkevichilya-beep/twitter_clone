"""Модуль конфигурации тестовой среды Pytest.

Инициализирует изолированную базу данных SQLite в оперативной памяти (in-memory),
настраивает автоматическое создание и удаление таблиц для каждого теста,
а также предоставляет асинхронный клиент HTTPX для имитации запросов к API.
"""

import os
import sys
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from database import Base, get_db_session
from main import app
from models import User

TEST_DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db() -> AsyncGenerator[None, None]:
    """Автоматически создает структуру таблиц перед тестом и удаляет её после.

    Yields:
        None: Передача управления тесту после развертывания схемы базы данных.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Предоставляет изолированную асинхронную сессию тестовой базы данных.

    Yields:
        AsyncSession: Сессия SQLAlchemy для выполнения тестовых транзакций.
    """
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Создает асинхронный клиент HTTPX с подменой основной сессии БД на тестовую.

    Args:
        db_session: Изолированная тестовая сессия базы данных.

    Yields:
        AsyncClient: Асинхронный клиент для отправки HTTP-запросов к приложению.
    """

    async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = _get_test_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def test_users(db_session: AsyncSession) -> tuple[User, User]:
    """Создает двух демонстрационных пользователей в тестовой базе данных.

    Args:
        db_session: Изолированная тестовая сессия базы данных.

    Returns:
        tuple[User, User]: Кортеж из двух созданных объектов пользователей.
    """
    u1: User = User(name="User One", api_key="test_key_1")
    u2: User = User(name="User Two", api_key="test_key_2")
    db_session.add_all([u1, u2])
    await db_session.commit()
    return u1, u2
