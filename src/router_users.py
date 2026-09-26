"""Модуль роутера для обработки HTTP-запросов, связанных с пользователями.

Реализует эндпоинты для работы с профилями пользователей, авторизации
по API-ключу, а также механизмы подписок и отписок между аккаунтами.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db_session
from models import User
from schemas import BaseResponse, UserResponse

router = APIRouter(prefix="/api/users", tags=["Пользователи"])


async def get_current_user(
    api_key: str = Header(..., alias="api-key"),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Аутентифицирует пользователя по уникальному API-ключу из заголовка.

    Args:
        api_key: Уникальный токен аутентификации, переданный в HTTP-заголовке.
        session: Текущая асинхронная сессия подключения к базе данных.

    Returns:
        User: Объект авторизованного пользователя из базы данных.

    Raises:
        HTTPException: Если пользователь с предоставленным ключом не найден.
    """
    stmt = select(User).where(User.api_key == api_key)
    res = await session.execute(stmt)
    current_user = res.scalar_one_or_none()

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный API-ключ",
        )
    return current_user


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool | User]:
    """Возвращает детальную информацию о профиле текущего пользователя.

    Args:
        current_user: Объект текущего авторизованного пользователя.
        session: Текущая асинхронная сессия подключения к базе данных.

    Returns:
        dict[str, bool | User]: Словарь со статусом операции и данными профиля.
    """
    stmt = (
        select(User)
        .where(User.id == current_user.id)
        .options(selectinload(User.followers), selectinload(User.following))
    )
    res = await session.execute(stmt)
    db_user = res.scalar_one()
    return {"result": True, "user": db_user}


@router.get("/{id}", response_model=UserResponse)
async def get_user_profile(
    id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool | User]:
    """Возвращает информацию о профиле произвольного пользователя.

    Args:
        id: Уникальный идентификатор искомого пользователя.
        current_user: Объект текущего авторизованного пользователя.
        session: Текущая асинхронная сессия подключения к базе данных.

    Returns:
        dict[str, bool | User]: Словарь со статусом операции и данными профиля.

    Raises:
        HTTPException: Если запрашиваемый пользователь отсутствует в базе данных.
    """
    stmt = (
        select(User)
        .where(User.id == id)
        .options(selectinload(User.followers), selectinload(User.following))
    )
    res = await session.execute(stmt)
    target_user = res.scalar_one_or_none()

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    return {"result": True, "user": target_user}


@router.post(
    "/{id}/follow",
    response_model=BaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def follow_user(
    id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    """Создает подписку текущего пользователя на указанного пользователя.

    Args:
        id: Уникальный идентификатор пользователя, на которого оформляется подписка.
        current_user: Объект текущего авторизованного пользователя.
        session: Текущая асинхронная сессия подключения к базе данных.

    Returns:
        dict[str, bool]: Словарь с флагом успешного выполнения операции.

    Raises:
        HTTPException: Если пользователь пытается подписаться на самого себя
            или если целевой аккаунт не существует в системе.
    """
    if current_user.id == id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя подписаться на себя",
        )

    stmt = select(User).where(User.id == id).options(selectinload(User.followers))
    res = await session.execute(stmt)
    target = res.scalar_one_or_none()

    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    await session.refresh(current_user, ["following"])

    if target not in current_user.following:
        current_user.following.append(target)
        await session.commit()

    return {"result": True}


@router.delete("/{id}/follow", response_model=BaseResponse)
async def unfollow_user(
    id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    """Удаляет существующую подписку текущего пользователя на указанного пользователя.

    Args:
        id: Уникальный идентификатор пользователя, от которого оформляется отписка.
        current_user: Объект текущего авторизованного пользователя.
        session: Текущая асинхронная сессия подключения к базе данных.

    Returns:
        dict[str, bool]: Словарь с флагом успешного выполнения операции.

    Raises:
        HTTPException: Если целевой аккаунт не существует в системе.
    """
    stmt = select(User).where(User.id == id)
    res = await session.execute(stmt)
    target = res.scalar_one_or_none()

    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    await session.refresh(current_user, ["following"])

    if target in current_user.following:
        current_user.following.remove(target)
        await session.commit()

    return {"result": True}
