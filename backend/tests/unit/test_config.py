import pytest

from app.core.config import Settings


def test_dev_env_allows_default_secret_key() -> None:
    settings = Settings(app_env="dev")
    assert settings.secret_key


def test_prod_env_refuses_default_secret_key() -> None:
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(app_env="prod", secret_key="change-me-to-a-random-64-char-string")


def test_prod_env_refuses_short_secret_key() -> None:
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(app_env="prod", secret_key="too-short")


def test_prod_env_refuses_default_database_url_password() -> None:
    with pytest.raises(ValueError, match="DATABASE_URL"):
        Settings(
            app_env="prod",
            secret_key="a" * 64,
            database_url="postgresql+psycopg://ems:change-me@postgres:5432/ems",
        )


def test_prod_env_accepts_real_secrets() -> None:
    settings = Settings(
        app_env="prod",
        secret_key="a" * 64,
        database_url="postgresql+psycopg://ems:a-real-generated-password@postgres:5432/ems",
    )
    assert settings.app_env == "prod"
