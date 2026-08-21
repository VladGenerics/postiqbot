"""Конфигурация приложения. Значения берутся из переменных окружения / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

UNLIMITED = 999_999


def fmt_limit(n: int) -> str:
    """Число или ∞ для безлимита."""
    return "∞" if n >= UNLIMITED else str(n)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str

    database_url: str

    google_client_id: str = ""
    google_client_secret: str = ""
    oauth_redirect_uri: str = "http://localhost:8080/oauth/callback"

    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_redirect_uri: str = "http://localhost:8080/tiktok/callback"
    tiktok_cookies_file: str = ""
    tiktok_direct_post: bool = False
    tiktok_direct_any_source: bool = True

    fernet_key: str

    web_host: str = "0.0.0.0"
    web_port: int = 8080
    public_domain: str = ""
    site_app_name: str = "PosttiqBot"

    privacy_url: str = "https://telegra.ph/Politika-konfidencialnosti-06-21-31"
    terms_url: str = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"
    support_contact: str = ""

    support_bot_token: str = ""
    support_group_id: int = 0
    support_bot_username: str = ""

    platega_merchant_id: str = ""
    platega_secret: str = ""
    platega_base_url: str = "https://app.platega.io"
    platega_callback_url: str = ""

    monitor_interval_minutes: int = 10
    publish_interval_minutes: int = 5

    daily_upload_quota: int = 6

    per_account_daily_limit: int = 4

    forever_days: int = 36500

    ytdlp_cookies_file: str = ""

    download_dir: str = "downloads"

    ai_api_key: str = ""
    ai_base_url: str = "https://api.freemodel.dev"
    ai_model: str = "gpt-5.5"
    ai_titles_enabled: bool = False

    admin_ids: str = ""

    private_mode: bool = False
    private_message: str = ""

    trial_days: int = 7
    trial_accounts: int = 1
    trial_videos: int = 4

    referral_bonus_days: int = 14
    referral_bonus_plan: str = "starter"

    gate_enabled: bool = True
    gate_channel: str = "@postiq_channel"
    gate_channel_url: str = "https://t.me/postiq_channel"

    @property
    def gate_link(self) -> str:
        """Ссылка «Перейти в канал»: gate_channel_url или https://t.me/<user>."""
        if self.gate_channel_url:
            return self.gate_channel_url
        ch = self.gate_channel.lstrip("@")
        return f"https://t.me/{ch}" if ch and not ch.startswith("-") else ""

    @property
    def gate_active(self) -> bool:
        return self.gate_enabled and bool(self.gate_channel)

    @property
    def plans(self) -> dict[str, dict]:
        """Тарифные планы."""
        return {
            "starter": {"emoji": "🟢", "name": "Starter", "accounts": 4, "videos": 4, "priority": 0,
                        "month": {"rub": 99, "stars": 59}, "forever": {"rub": 399, "stars": 259}},
            "pro": {"emoji": "🔵", "name": "Pro", "accounts": 10, "videos": 10, "priority": 1,
                    "month": {"rub": 199, "stars": 129}, "forever": {"rub": 799, "stars": 499}},
            "premium": {"emoji": "🟣", "name": "Premium", "accounts": UNLIMITED, "videos": UNLIMITED, "priority": 2,
                        "month": {"rub": 399, "stars": 259}, "forever": {"rub": 1499, "stars": 999}},
        }

    def plan_days(self, period: str) -> int:
        """Срок в днях по периоду: forever → forever_days, иначе 30."""
        return self.forever_days if period == "forever" else 30

    def plan_price(self, plan: str, period: str, currency: str) -> int:
        """Цена плана: currency = 'rub' | 'stars'."""
        p = self.plans[plan][period]
        return p["stars"] if currency == "stars" else p["rub"]

    def plan_label(self, plan: str) -> str:
        p = self.plans[plan]
        return f"{p['emoji']} {p['name']}"

    @property
    def referral_bonus_label(self) -> str:
        """Подпись бонусного тарифа рефералки («🟢 Starter») для текстов бота."""
        plan = self.referral_bonus_plan
        return self.plan_label(plan) if plan in self.plans else plan

    @property
    def admin_id_set(self) -> set[int]:
        return {
            int(x) for x in self.admin_ids.replace(" ", "").split(",") if x
        }


@lru_cache
def get_settings() -> Settings:
    """Закэшированный синглтон настроек."""
    return Settings()  # type: ignore[call-arg]
