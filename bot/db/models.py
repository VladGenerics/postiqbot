"""SQLAlchemy-модели PostiqBot."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
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
    trial_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    subscription_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    referred_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    referral_rewarded: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    tier_accounts: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    tier_videos: Mapped[int] = mapped_column(Integer, default=4, server_default="4")
    videos_used: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tier_priority: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    tier_plan: Mapped[str | None] = mapped_column(String(16), nullable=True)
    lang: Mapped[str] = mapped_column(String(2), default="ru", server_default="ru")
    expiry_warned: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    channel_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    promo_code: Mapped[str | None] = mapped_column(String(32), nullable=True)

    publish_accounts: Mapped[list["PublishAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    connections: Mapped[list["Connection"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    folders: Mapped[list["Folder"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Folder(Base):
    """Папка для группировки связок пользователя."""

    __tablename__ = "folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="folders")
    connections: Mapped[list["Connection"]] = relationship(back_populates="folder")


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
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), index=True
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
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), index=True
    )
    publish_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("publish_accounts.id", ondelete="CASCADE")
    )
    source_channel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("source_channels.id", ondelete="CASCADE")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    privacy: Mapped[str] = mapped_column(String(16), default="public")
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    folder_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("folders.id", ondelete="SET NULL"), nullable=True
    )

    schedule_mode: Mapped[str] = mapped_column(
        String(16), default="immediate", server_default="immediate"
    )
    interval_minutes: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    post_times: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tz: Mapped[str] = mapped_column(String(48), default="UTC", server_default="UTC")

    tt_auto: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    tt_privacy: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tt_disable_comment: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    tt_disable_duet: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    tt_disable_stitch: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    tt_brand_organic: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    tt_brand_content: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    tt_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    overlay_file_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    overlay_position: Mapped[str | None] = mapped_column(String(16), nullable=True)
    overlay_scale: Mapped[int] = mapped_column(
        Integer, default=30, server_default="30"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="connections")
    folder: Mapped["Folder | None"] = relationship(back_populates="connections")
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
JOB_AWAITING = "awaiting"
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
        Index("ix_jobs_status_updated_at", "status", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("connections.id", ondelete="CASCADE"), index=True
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
    yt_resumable_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    download_attempts: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    publish_attempts: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    tt_privacy: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tt_disable_comment: Mapped[bool] = mapped_column(Boolean, default=True)
    tt_disable_duet: Mapped[bool] = mapped_column(Boolean, default=True)
    tt_disable_stitch: Mapped[bool] = mapped_column(Boolean, default=True)
    tt_brand_organic: Mapped[bool] = mapped_column(Boolean, default=False)
    tt_brand_content: Mapped[bool] = mapped_column(Boolean, default=False)
    tt_publish_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    awaiting_since: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    card_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    connection: Mapped["Connection"] = relationship(back_populates="jobs")


PAY_PENDING = "pending"
PAY_PAID = "paid"
PAY_FAILED = "failed"


class Payment(Base):
    """Платёж через внешнего провайдера (Platega) или Telegram Stars."""

    __tablename__ = "payments"
    __table_args__ = (
        Index(
            "uq_payments_provider_tx",
            "provider",
            "provider_payment_id",
            unique=True,
            postgresql_where=text("provider_payment_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    days: Mapped[int] = mapped_column(Integer)
    plan: Mapped[str | None] = mapped_column(String(16), nullable=True)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(
        String(8), default="RUB", server_default="RUB"
    )
    provider: Mapped[str] = mapped_column(
        String(16), default="platega", server_default="platega"
    )
    provider_payment_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default=PAY_PENDING, server_default=PAY_PENDING, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    granted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    promo_code: Mapped[str | None] = mapped_column(String(32), nullable=True)


class SupportMessage(Base):
    """История обращений в поддержку. Хранит переписку user↔admin."""

    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    photo_file_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class SupportThread(Base):
    """Маппинг пользователь ↔ тема (forum topic) в группе поддержки."""

    __tablename__ = "support_threads"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    topic_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PromoCode(Base):
    """Промокод на скидку."""

    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    percent: Mapped[int] = mapped_column(Integer)
    plan: Mapped[str | None] = mapped_column(String(16), nullable=True)
    max_uses: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    used_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PromoRedemption(Base):
    """Факт списания промокода: один код — один раз на пользователя."""

    __tablename__ = "promo_redemptions"
    __table_args__ = (
        UniqueConstraint("promo_id", "user_id", name="uq_promo_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    promo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("promo_codes.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    payment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

