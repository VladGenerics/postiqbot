"""Конфигурация приложения. Значения берутся из переменных окружения / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    fernet_key: str

    web_host: str = "0.0.0.0"
    web_port: int = 8080

    monitor_interval_minutes: int = 10
    publish_interval_minutes: int = 5

    daily_upload_quota: int = 6

    download_dir: str = "downloads"

    admin_ids: str = ""

    trial_days: int = 2
    trial_accounts: int = 1
    trial_videos: int = 5

    sub_stars_7: int = 99
    sub_accounts_7: int = 2
    sub_videos_7: int = 40
    sub_stars_14: int = 179
    sub_accounts_14: int = 3
    sub_videos_14: int = 100
    sub_stars_30: int = 299
    sub_accounts_30: int = 5
    sub_videos_30: int = 300

    referral_bonus_days: int = 7

    @property
    def sub_tiers(self) -> dict[int, dict[str, int]]:
        """{дни: {stars, accounts, videos}}."""
        return {
            7: {"stars": self.sub_stars_7, "accounts": self.sub_accounts_7, "videos": self.sub_videos_7},
            14: {"stars": self.sub_stars_14, "accounts": self.sub_accounts_14, "videos": self.sub_videos_14},
            30: {"stars": self.sub_stars_30, "accounts": self.sub_accounts_30, "videos": self.sub_videos_30},
        }

    @property
    def admin_id_set(self) -> set[int]:
        return {
            int(x) for x in self.admin_ids.replace(" ", "").split(",") if x
        }


@lru_cache
def get_settings() -> Settings:
    """Закэшированный синглтон настроек."""
    return Settings()  # type: ignore[call-arg]
