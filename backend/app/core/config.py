from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = "ems"
    postgres_password: str = "change-me"
    postgres_db: str = "ems"
    database_url: str = "postgresql+psycopg://ems:change-me@localhost:5432/ems"

    secret_key: str = "change-me-to-a-random-64-char-string"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    app_env: Literal["dev", "test", "prod"] = "dev"
    default_locale: Literal["ar", "en"] = "ar"


@lru_cache
def get_settings() -> Settings:
    return Settings()
