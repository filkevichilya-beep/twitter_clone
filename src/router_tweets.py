"""Модуль роутера для обработки HTTP-запросов, связанных с твитами и медиафайлами.

Реализует эндпоинты для публикации твитов, загрузки графических вложений,
удаления публикаций, а также механизмы добавления и удаления отметок 'Нравится'.
"""

import os
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db_session
from models import Like, Media, Tweet, User
from router_users import get_current_user
from schemas import BaseResponse, TweetCreate, TweetCreateResponse, TweetListResponse

router = APIRouter(prefix="/api", tags=["Твиты и медиа"])


@router.post("/medias", status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool | int]:
    """Загрузка медиафайла на сервер с сохранением на диск и регистрацией в базе данных.

    Args:
        file: Загружаемый объект файла (multipart/form-data).
        current_user: Объект текущего авторизованного пользователя.
        session: Текущая асинхронная сессия подключения к базе данных.

    Returns:
        dict[str, bool | int]: Словарь со статусом операции и
            идентификатором медиафайла.
    """
    base_dir = Path(__file__).resolve().parent.parent
    medias_dir = base_dir / "static" / "medias"
    medias_dir.mkdir(parents=True, exist_ok=True)

    db_media = Media(file_path="temp")
    session.add(db_media)
    await session.commit()

    filename = file.filename or "image.jpg"
    _, file_ext = os.path.splitext(filename)
    saved_filename = f"media_{db_media.id}{file_ext}"
    full_path = medias_dir / saved_filename

    async with aiofiles.open(full_path, "wb") as buffer:
        content = await file.read()
        await buffer.write(content)

    db_media.file_path = f"/static/medias/{saved_filename}"
    await session.commit()

    return {"result": True, "media_id": db_media.id}


@router.post(
    "/tweets",
    response_model=TweetCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tweet(
    tweet: TweetCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool | int]:
    """Создание новой текстовой публикации с возможностью привязки медиафайлов.

    Args:
        tweet: Pydantic-схема с текстовым контентом и списком ID медиафайлов.
        current_user: Объект текущего авторизованного пользователя.
        session: Текущая асинхронная сессия подключения к базе данных.

    Returns:
        dict[str, bool | int]: Словарь со статусом операции и идентификатором твита.
    """
    new_tweet = Tweet(content=tweet.tweet_data, author_id=current_user.id)
    session.add(new_tweet)
    await session.flush()

    if tweet.tweet_media_ids:
        stmt = select(Media).where(Media.id.in_(tweet.tweet_media_ids))
        res = await session.execute(stmt)
        medias = res.scalars().all()
        for media in medias:
            media.tweet_id = new_tweet.id

    await session.commit()
    return {"result": True, "tweet_id": new_tweet.id}


@router.delete("/tweets/{id}", response_model=BaseResponse)
async def delete_tweet(
    id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    """Удаление публикации, если текущий пользователь является её автором.

    Args:
        id: Уникальный идентификатор удаляемого твита.
        current_user: Объект текущего авторизованного пользователя.
        session: Текущая асинхронная сессия подключения к базе данных.

    Returns:
        dict[str, bool]: Словарь с флагом успешного выполнения операции.

    Raises:
        HTTPException: Если твит не найден или пользователь не является автором.
    """
    stmt = select(Tweet).where(Tweet.id == id)
    res = await session.execute(stmt)
    target_tweet = res.scalar_one_or_none()

    if target_tweet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Твит не найден",
        )

    if target_tweet.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя удалить чужой твит",
        )

    await session.delete(target_tweet)
    await session.commit()
    return {"result": True}


@router.post("/tweets/{id}/likes", response_model=BaseResponse)
async def like_tweet(
    id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    """Установка отметки 'Нравится' к указанной публикации.

    Args:
        id: Уникальный идентификатор оцениваемого твита.
        current_user: Объект текущего авторизованного пользователя.
        session: Текущая асинхронная сессия подключения к базе данных.

    Returns:
        dict[str, bool]: Словарь с флагом успешного выполнения операции.

    Raises:
        HTTPException: Если оцениваемый твит отсутствует в базе данных.
    """
    target_tweet = await session.get(Tweet, id)
    if target_tweet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Твит не найден",
        )

    stmt = select(Like).where(Like.user_id == current_user.id, Like.tweet_id == id)
    res = await session.execute(stmt)
    if res.scalar_one_or_none() is not None:
        return {"result": True}

    new_like = Like(user_id=current_user.id, tweet_id=id)
    session.add(new_like)
    await session.commit()
    return {"result": True}


@router.delete("/tweets/{id}/likes", response_model=BaseResponse)
async def unlike_tweet(
    id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    """Удаление отметки 'Нравится' с указанной публикации.

    Args:
        id: Уникальный идентификатор твита, с которого снимается лайк.
        current_user: Объект текущего авторизованного пользователя.
        session: Текущая асинхронная сессия подключения к базе данных.

    Returns:
        dict[str, bool]: Словарь с флагом успешного выполнения операции.
    """
    stmt = select(Like).where(Like.user_id == current_user.id, Like.tweet_id == id)
    res = await session.execute(stmt)
    existing_like = res.scalar_one_or_none()

    if existing_like is not None:
        await session.delete(existing_like)
        await session.commit()

    return {"result": True}


@router.get("/tweets", response_model=TweetListResponse)
async def get_tweets_feed(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool | list[dict[str, Any]]]:
    """Получение глобальной ленты публикаций с сортировкой по популярности.

    Args:
        current_user: Объект текущего авторизованного пользователя.
        session: Текущая асинхронная сессия подключения к базе данных.

    Returns:
        dict[str, bool | list[dict[str, Any]]]: Словарь с лентой твитов.
    """
    stmt = (
        select(Tweet)
        .join(Like, isouter=True)
        .group_by(Tweet.id)
        .order_by(func.count(Like.id).desc(), Tweet.id.desc())
        .options(
            selectinload(Tweet.author),
            selectinload(Tweet.attachments),
            selectinload(Tweet.likes).selectinload(Like.user),
        )
    )
    res = await session.execute(stmt)
    tweets_db = res.scalars().all()

    formatted_tweets = []
    for t in tweets_db:
        formatted_tweets.append(
            {
                "id": t.id,
                "content": t.content,
                "author": {"id": t.author.id, "name": t.author.name},
                "attachments": [media.file_path for media in t.attachments],
                "likes": [
                    {"user_id": like.user.id, "name": like.user.name}
                    for like in t.likes
                ],
            }
        )

    return {"result": True, "tweets": formatted_tweets}
