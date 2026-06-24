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

    @property
    def admin_id_set(self) -> set[int]:
        return {
            int(x) for x in self.admin_ids.replace(" ", "").split(",") if x
        }


@lru_cache
def get_settings() -> Settings:
    """Закэшированный синглтон настроек."""
    return Settings()  # type: ignore[call-arg]
