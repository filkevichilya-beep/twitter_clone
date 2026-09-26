"""Модуль автоматизированного тестирования бизнес-логики сервиса микроблогов.

Содержит полный пакет асинхронных интеграционных тестов, покрывающих
все ключевые сценарии использования API: аутентификацию, работу с профилями,
публикацию и удаление твитов, управление лайками, подписками и медиафайлами.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Tweet, User


@pytest.mark.asyncio
async def test_auth_failed(client: AsyncClient) -> None:
    """Проверяет отклонение запроса при передаче некорректного API-ключа.

    Отправляет GET-запрос на получение данных профиля с невалидным токеном
    и ожидает получить HTTP-статус 401 Unauthorized и флаг результата False.

    Args:
        client: Асинхронный клиент HTTPX для отправки запросов.
    """
    response = await client.get("/api/users/me", headers={"api-key": "invalid"})
    assert response.status_code == 401
    assert response.json()["result"] is False


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, test_users: tuple[User, User]) -> None:
    """Проверяет успешное получение информации о профиле текущего пользователя.

    Убеждается, что при валидном API-ключе бэкенд возвращает статус 200 OK,
    корректное имя авторизованного аккаунта и флаг успешного выполнения.

    Args:
        client: Асинхронный клиент HTTPX для отправки запросов.
        test_users: Кортеж с предварительно созданными тестовыми пользователями.
    """
    response = await client.get("/api/users/me", headers={"api-key": "test_key_1"})
    assert response.status_code == 200
    data = response.json()
    assert data["result"] is True
    assert data["user"]["name"] == "User One"


@pytest.mark.asyncio
async def test_get_user_by_id(
    client: AsyncClient,
    test_users: tuple[User, User],
) -> None:
    """Проверяет получение информации о чужом профиле по его идентификатору.

    Args:
        client: Асинхронный клиент HTTPX для отправки запросов.
        test_users: Кортеж с предварительно созданными тестовыми пользователями.
    """
    _, u2 = test_users
    response = await client.get(
        f"/api/users/{u2.id}",
        headers={"api-key": "test_key_1"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["name"] == "User Two"


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(
    client: AsyncClient, test_users: tuple[User, User]
) -> None:
    """Проверяет возврат ошибки 404 при запросе несуществующего профиля.

    Args:
        client: Асинхронный клиент HTTPX для отправки запросов.
        test_users: Кортеж с предварительно созданными тестовыми пользователями.
    """
    response = await client.get(
        "/api/users/9999",
        headers={"api-key": "test_key_1"},
    )
    assert response.status_code == 404
    assert response.json()["result"] is False


@pytest.mark.asyncio
async def test_follow_unfollow_cycle(
    client: AsyncClient,
    test_users: tuple[User, User],
    db_session: AsyncSession,
) -> None:
    """Проверяет полный цикл социальной активности: подписку и отписку.

    Имитирует подписку User One на User Two, проверяет изменение списков
    взаимосвязей в профиле, тестирует защиту от дублирования подписок,
    а затем выполняет отписку и проверяет возврат к исходному состоянию.

    Args:
        client: Асинхронный клиент HTTPX для отправки запросов.
        test_users: Кортеж с предварительно созданными тестовыми пользователями.
        db_session: Изолированная тестовая сессия базы данных.
    """
    _, u2 = test_users

    res = await client.post(
        f"/api/users/{u2.id}/follow",
        headers={"api-key": "test_key_1"},
    )
    assert res.status_code == 201

    res_me = await client.get("/api/users/me", headers={"api-key": "test_key_1"})
    assert len(res_me.json()["user"]["following"]) == 1

    res_duplicate = await client.post(
        f"/api/users/{u2.id}/follow",
        headers={"api-key": "test_key_1"},
    )
    assert res_duplicate.status_code == 201

    res_un = await client.delete(
        f"/api/users/{u2.id}/follow",
        headers={"api-key": "test_key_1"},
    )
    assert res_un.status_code == 200

    res_me2 = await client.get("/api/users/me", headers={"api-key": "test_key_1"})
    assert len(res_me2.json()["user"]["following"]) == 0

    res_un_duplicate = await client.delete(
        f"/api/users/{u2.id}/follow",
        headers={"api-key": "test_key_1"},
    )
    assert res_un_duplicate.status_code == 200


@pytest.mark.asyncio
async def test_follow_self_error(
    client: AsyncClient, test_users: tuple[User, User]
) -> None:
    """Проверяет запрет на подписку пользователя на самого себя.

    Args:
        client: Асинхронный клиент HTTPX для отправки запросов.
        test_users: Кортеж с предварительно созданными тестовыми пользователями.
    """
    u1, _ = test_users
    res = await client.post(
        f"/api/users/{u1.id}/follow",
        headers={"api-key": "test_key_1"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_follow_user_not_found(
    client: AsyncClient, test_users: tuple[User, User]
) -> None:
    """Проверяет обработку попытки подписки на несуществующего пользователя.

    Args:
        client: Асинхронный клиент HTTPX для отправки запросов.
        test_users: Кортеж с предварительно созданными тестовыми пользователями.
    """
    res = await client.post(
        "/api/users/9999/follow",
        headers={"api-key": "test_key_1"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_unfollow_user_not_found(
    client: AsyncClient, test_users: tuple[User, User]
) -> None:
    """Проверяет обработку попытки отписки от несуществующего пользователя.

    Args:
        client: Асинхронный клиент HTTPX для отправки запросов.
        test_users: Кортеж с предварительно созданными тестовыми пользователями.
    """
    res = await client.delete(
        "/api/users/9999/follow",
        headers={"api-key": "test_key_1"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_create_and_delete_tweet(
    client: AsyncClient,
    test_users: tuple[User, User],
    db_session: AsyncSession,
) -> None:
    """Проверяет успешное создание публикации и её последующее удаление автором.

    Args:
        client: Асинхронный клиент HTTPX для отправки запросов.
        test_users: Кортеж с предварительно созданными тестовыми пользователями.
        db_session: Изолированная тестовая сессия базы данных.
    """
    res = await client.post(
        "/api/tweets",
        headers={"api-key": "test_key_1"},
        json={"tweet_data": "Hello World", "tweet_media_ids": []},
    )
    assert res.status_code == 201
    tweet_id = res.json()["tweet_id"]

    del_res = await client.delete(
        f"/api/tweets/{tweet_id}",
        headers={"api-key": "test_key_1"},
    )
    assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_delete_tweet_not_found(
    client: AsyncClient, test_users: tuple[User, User]
) -> None:
    """Проверяет возврат ошибки 404 при удалении несуществующего твита.

    Args:
        client: Асинхронный клиент HTTPX для отправки запросов.
        test_users: Кортеж с предварительно созданными тестовыми пользователями.
    """
    res = await client.delete("/api/tweets/9999", headers={"api-key": "test_key_1"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_delete_foreign_tweet_forbidden(
    client: AsyncClient,
    test_users: tuple[User, User],
    db_session: AsyncSession,
) -> None:
    """Проверяет запрет и статус 403 при попытке удаления чужого твита.

    Args:
        client: Асинхронный клиент HTTPX для отправки запросов.
        test_users: Кортеж с предварительно созданными тестовыми пользователями.
        db_session: Изолированная тестовая сессия базы данных.
    """
    u1, _ = test_users
    tweet = Tweet(content="User One Tweet", author_id=u1.id)
    db_session.add(tweet)
    await db_session.commit()

    res = await client.delete(
        f"/api/tweets/{tweet.id}",
        headers={"api-key": "test_key_2"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_like_unlike_tweet(
    client: AsyncClient,
    test_users: tuple[User, User],
    db_session: AsyncSession,
) -> None:
    """Проверяет полный цикл работы с отметками 'Нравится' (лайк/анлайк).

    Args:
        client: Асинхронный клиент HTTPX для отправки запросов.
        test_users: Кортеж с предварительно созданными тестовыми пользователями.
        db_session: Изолированная тестовая сессия базы данных.
    """
    u1, _ = test_users
    tweet = Tweet(content="Test Tweet", author_id=u1.id)
    db_session.add(tweet)
    await db_session.commit()

    res = await client.post(
        f"/api/tweets/{tweet.id}/likes",
        headers={"api-key": "test_key_2"},
    )
    assert res.status_code == 200

    res_dup = await client.post(
        f"/api/tweets/{tweet.id}/likes",
        headers={"api-key": "test_key_2"},
    )
    assert res_dup.status_code == 200

    feed = await client.get("/api/tweets", headers={"api-key": "test_key_1"})
    assert len(feed.json()["tweets"][0]["likes"]) == 1

    res_un = await client.delete(
        f"/api/tweets/{tweet.id}/likes",
        headers={"api-key": "test_key_2"},
    )
    assert res_un.status_code == 200


@pytest.mark.asyncio
async def test_like_tweet_not_found(
    client: AsyncClient, test_users: tuple[User, User]
) -> None:
    """Проверяет ошибку 404 при попытке поставить лайк несуществующему твиту.

    Args:
        client: Асинхронный клиент HTTPX для отправки запросов.
        test_users: Кортеж с предварительно созданными тестовыми пользователями.
    """
    res = await client.post(
        "/api/tweets/9999/likes",
        headers={"api-key": "test_key_1"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_upload_media(client: AsyncClient, test_users: tuple[User, User]) -> None:
    """Проверяет успешную обработку загрузки бинарных медиафайлов (изображений).

    Args:
        client: Асинхронный клиент HTTPX для отправки запросов.
        test_users: Кортеж с предварительно созданными тестовыми пользователями.
    """
    files = {"file": ("test.png", b"fake-bytes", "image/png")}
    res = await client.post(
        "/api/medias",
        headers={"api-key": "test_key_1"},
        files=files,
    )
    assert res.status_code == 201
    assert "media_id" in res.json()


@pytest.mark.asyncio
async def test_validation_error_handler(
    client: AsyncClient,
    test_users: tuple[User, User],
) -> None:
    """Проверяет работу кастомного перехватчика ошибок валидации Pydantic.

    Передаёт невалидную структуру тела запроса и ожидает получить
    HTTP-статус 400 Bad Request и кастомный тип ошибки ValidationError.

    Args:
        client: Асинхронный клиент HTTPX для отправки запросов.
        test_users: Кортеж с предварительно созданными тестовыми пользователями.
    """
    res = await client.post(
        "/api/tweets",
        headers={"api-key": "test_key_1"},
        json={"tweet_data": 12345},
    )
    assert res.status_code == 400
    assert res.json()["result"] is False
    assert res.json()["error_type"] == "ValidationError"
