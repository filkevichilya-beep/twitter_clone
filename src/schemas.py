"""Модуль Pydantic-схем для валидации запросов и структурирования ответов API.

Обеспечивает строгий контроль типов входных данных от фронтенда и гарантирует
формирование JSON-ответов бэкенда в точном соответствии со спецификацией ТЗ.
"""

from pydantic import BaseModel, ConfigDict, Field


class BaseResponse(BaseModel):
    """Базовая схема успешного ответа сервера."""

    result: bool = True


class ErrorResponse(BaseModel):
    """Схема ответа сервера при возникновении ошибки."""

    result: bool = False
    error_type: str
    error_message: str


class UserShortOut(BaseModel):
    """Схема с базовой информацией о пользователе для вложенных списков."""

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserDetail(UserShortOut):
    """Схема с подробной информацией о профиле пользователя."""

    followers: list[UserShortOut] = Field(default_factory=list)
    following: list[UserShortOut] = Field(default_factory=list)


class UserResponse(BaseResponse):
    """Финальная схема ответа сервера с данными профиля пользователя."""

    user: UserDetail


class TweetCreate(BaseModel):
    """Схема для проверки данных при создании нового твита."""

    tweet_data: str = Field(..., min_length=1)
    tweet_media_ids: list[int] = Field(default_factory=list)


class TweetCreateResponse(BaseResponse):
    """Схема ответа сервера после успешного создания твита."""

    tweet_id: int


class LikeOut(BaseModel):
    """Схема вывода информации о лайке в ленте твитов."""

    user_id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class TweetOut(BaseModel):
    """Схема вывода полной информации о твите в ленте."""

    id: int
    content: str
    attachments: list[str] = Field(default_factory=list)
    author: UserShortOut
    likes: list[LikeOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TweetListResponse(BaseResponse):
    """Финальная схема ответа сервера со списком твитов ленты."""

    tweets: list[TweetOut]
