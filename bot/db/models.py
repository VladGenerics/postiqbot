"""SQLAlchemy-модели PostiqBot."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    """Пользователь Telegram (клиент бота)."""

    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    publish_accounts: Mapped[list["PublishAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    connections: Mapped[list["Connection"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class OAuthProject(Base):
    """Google Cloud проект из пула."""

    __tablename__ = "oauth_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    client_id: Mapped[str] = mapped_column(String(255), unique=True)
    client_secret_enc: Mapped[str] = mapped_column(Text)
    owner_telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=True
    )
    daily_quota: Mapped[int] = mapped_column(Integer, default=6)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    publish_accounts: Mapped[list["PublishAccount"]] = relationship(
        back_populates="project"
    )


class PublishAccount(Base):
    """Канал клиента, КУДА публикуем. Привязан к проекту из пула."""

    __tablename__ = "publish_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "platform", "channel_id", name="uq_publish_channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE")
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("oauth_projects.id", ondelete="RESTRICT"), nullable=True
    )
    platform: Mapped[str] = mapped_column(String(16), default="youtube")
    channel_id: Mapped[str] = mapped_column(String(64))
    channel_title: Mapped[str] = mapped_column(String(255))
    refresh_token_enc: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="publish_accounts")
    project: Mapped["OAuthProject"] = relationship(back_populates="publish_accounts")
    connections: Mapped[list["Connection"]] = relationship(
        back_populates="publish_account", cascade="all, delete-orphan"
    )


class SourceChannel(Base):
    """Канал, ЗА которым следим (источник видео)."""

    __tablename__ = "source_channels"
    __table_args__ = (
        UniqueConstraint("platform", "channel_id", name="uq_source_channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(16), default="youtube")
    channel_id: Mapped[str] = mapped_column(String(64))
    channel_title: Mapped[str] = mapped_column(String(255))
    last_seen_video_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    connections: Mapped[list["Connection"]] = relationship(
        back_populates="source_channel"
    )


class Connection(Base):
    """Связка источник → канал публикации."""

    __tablename__ = "connections"
    __table_args__ = (
        UniqueConstraint(
            "publish_account_id", "source_channel_id", name="uq_connection"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE")
    )
    publish_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("publish_accounts.id", ondelete="CASCADE")
    )
    source_channel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("source_channels.id", ondelete="CASCADE")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    privacy: Mapped[str] = mapped_column(String(16), default="private")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="connections")
    publish_account: Mapped["PublishAccount"] = relationship(
        back_populates="connections"
    )
    source_channel: Mapped["SourceChannel"] = relationship(
        back_populates="connections"
    )
    jobs: Mapped[list["Job"]] = relationship(
        back_populates="connection", cascade="all, delete-orphan"
    )


JOB_PENDING = "pending"
JOB_DOWNLOADING = "downloading"
JOB_SCHEDULED = "scheduled"
JOB_PUBLISHING = "publishing"
JOB_PUBLISHED = "published"
JOB_FAILED = "failed"


class Job(Base):
    """Единица работы: одно исходное видео → одна публикация."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "source_video_id", name="uq_job_source_video"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("connections.id", ondelete="CASCADE")
    )
    source_video_id: Mapped[str] = mapped_column(String(64))
    video_url: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=JOB_PENDING, index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    youtube_video_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    connection: Mapped["Connection"] = relationship(back_populates="jobs")
