"""Модуль декларативных ORM-моделей базы данных для сервиса микроблогов.

Определяет структуру таблиц пользователей, твитов, медиафайлов и лайков,
а также описывает социальные связи и подписки типа Many-to-Many
в рамках асинхронного маппера SQLAlchemy 2.0.
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

followers_association = Table(
    "followers",
    Base.metadata,
    Column(
        "follower_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "following_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class User(Base):
    """ORM-модель пользователя корпоративной сети микроблогов.

    Хранит информацию о профиле, уникальном книге аутентификации API,
    а также управляет каскадными связями с твитами, отметками 'Нравится'
    и списками подписчиков/подписок (Self-Referential Many-to-Many).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    api_key: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )

    tweets: Mapped[list["Tweet"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
    likes: Mapped[list["Like"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    following: Mapped[list["User"]] = relationship(
        "User",
        secondary=followers_association,
        primaryjoin=id == followers_association.c.follower_id,
        secondaryjoin=id == followers_association.c.following_id,
        back_populates="followers",
    )

    followers: Mapped[list["User"]] = relationship(
        "User",
        secondary=followers_association,
        primaryjoin=id == followers_association.c.following_id,
        secondaryjoin=id == followers_association.c.follower_id,
        back_populates="following",
    )


class Media(Base):
    """ORM-модель для учета и хранения информации о загруженных медиафайлах.

    Фиксирует пути к файлам на сервере и связывает их со структурами твитов,
    позволяя прикреплять графические вложения к публикациям.
    """

    __tablename__ = "medias"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    tweet_id: Mapped[int | None] = mapped_column(
        ForeignKey("tweets.id", ondelete="CASCADE"), nullable=True
    )

    tweet: Mapped["Tweet | None"] = relationship(back_populates="attachments")


class Tweet(Base):
    """ORM-модель текстовых публикаций (твитов).

    Содержит текстовое наполнение твита, метаданные об авторе и списки
    связанных медиафайлов и лайков, поставленных другими пользователями.
    """

    __tablename__ = "tweets"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(String(1000), nullable=False)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    author: Mapped["User"] = relationship(back_populates="tweets")
    attachments: Mapped[list["Media"]] = relationship(
        back_populates="tweet", cascade="all, delete-orphan"
    )
    likes: Mapped[list["Like"]] = relationship(
        back_populates="tweet", cascade="all, delete-orphan"
    )


class Like(Base):
    """ORM-модель для регистрации отметок 'Нравится' к публикациям.

    Осуществляет связь Many-to-Many между пользователями и твитами.
    Снабжена уникальным составным ограничением, предотвращающим дублирование
    лайков от одного и того же аккаунта на один твит.
    """

    __tablename__ = "likes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tweet_id: Mapped[int] = mapped_column(
        ForeignKey("tweets.id", ondelete="CASCADE"), nullable=False
    )

    tweet: Mapped["Tweet"] = relationship(back_populates="likes")
    user: Mapped["User"] = relationship(back_populates="likes")

    __table_args__ = (
        UniqueConstraint("user_id", "tweet_id", name="uq_user_tweet_like"),
    )
