from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRET_KEY = "change-me-to-a-random-64-char-string"
_DEFAULT_POSTGRES_PASSWORD = "change-me"
_MIN_SECRET_KEY_LENGTH = 32
# DATABASE_URL, not the standalone POSTGRES_PASSWORD field, is what the app
# actually connects with — docker-compose.yml's backend service is only ever
# given DATABASE_URL, never POSTGRES_PASSWORD directly, so validating the
# latter alone would false-positive against a correctly configured deployment.
_DEFAULT_DATABASE_URL_PASSWORD_MARKER = f":{_DEFAULT_POSTGRES_PASSWORD}@"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = "ems"
    postgres_password: str = _DEFAULT_POSTGRES_PASSWORD
    postgres_db: str = "ems"
    database_url: str = "postgresql+psycopg://ems:change-me@localhost:5432/ems"

    secret_key: str = _DEFAULT_SECRET_KEY
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    app_env: Literal["dev", "test", "prod"] = "dev"
    default_locale: Literal["ar", "en"] = "ar"

    @model_validator(mode="after")
    def _refuse_insecure_prod_secrets(self) -> "Settings":
        # A forgotten placeholder here isn't a cosmetic issue: SECRET_KEY signs
        # every JWT, so the literal string committed in .env.example would let
        # anyone forge a valid access token for any user_id. Fail at startup
        # rather than run an auth system with a publicly-known signing key.
        if self.app_env != "prod":
            return self
        if self.secret_key == _DEFAULT_SECRET_KEY or len(self.secret_key) < _MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                "SECRET_KEY must be set to a real random secret "
                f"(>= {_MIN_SECRET_KEY_LENGTH} chars, not the .env.example placeholder) "
                "when APP_ENV=prod"
            )
        if _DEFAULT_DATABASE_URL_PASSWORD_MARKER in self.database_url:
            raise ValueError(
                "DATABASE_URL still contains the default 'change-me' password placeholder "
                "when APP_ENV=prod"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
