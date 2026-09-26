"""Модуль автоматической инициализации и первичного наполнения базы данных.

Создает необходимые таблицы в PostgreSQL при их отсутствии и заполняет базу
начальными демонстрационными пользователями с фиксированными API-ключами
для корректной интеграции с фронтенд-интерфейсом.
"""

import asyncio

from sqlalchemy import select

from database import Base, async_session_factory, engine
from models import User


async def init_models() -> None:
    """Проверяет структуру базы данных и создает отсутствующие таблицы ORM."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_data() -> None:
    """Заполняет базу данных начальными пользователями при их отсутствии."""
    async with async_session_factory() as session:
        stmt = select(User).limit(1)
        res = await session.execute(stmt)
        if res.scalar_one_or_none() is not None:
            return

        users = [
            User(name="Элон Маск", api_key="test"),
            User(name="Сергей Брин", api_key="test_key_1"),
            User(name="Павел Дуров", api_key="test_key_2"),
        ]
        session.add_all(users)
        await session.commit()


async def main() -> None:
    """Главная точка входа для выполнения скрипта инициализации."""
    await init_models()
    await seed_data()


if __name__ == "__main__":
    asyncio.run(main())
