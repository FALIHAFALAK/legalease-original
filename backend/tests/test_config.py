from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_postgres_urls_are_normalized_to_the_psycopg_driver():
    legacy = Settings(_env_file=None, database_url="postgres://user:pw@db.example.com:5432/legalease")
    standard = Settings(_env_file=None, database_url="postgresql://user:pw@db.example.com:5432/legalease")
    explicit = Settings(
        _env_file=None, database_url="postgresql+psycopg://user:pw@db.example.com:5432/legalease"
    )
    assert legacy.database_url == "postgresql+psycopg://user:pw@db.example.com:5432/legalease"
    assert standard.database_url == legacy.database_url
    assert explicit.database_url == legacy.database_url


def test_sqlite_url_is_left_untouched():
    assert Settings(_env_file=None, database_url="sqlite:///./legalease.db").database_url == (
        "sqlite:///./legalease.db"
    )


def production_settings(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "app_env": "production",
        "secret_key": "a" * 48,
        "session_cookie_secure": True,
        "cors_origins": "https://legalease.example.com",
        "database_url": "postgresql://user:pw@db.example.com:5432/legalease",
        "ai_provider": "gemini",
        "gemini_api_key": "g" * 32,
    }
    base.update(overrides)
    return base


def test_production_settings_are_accepted_when_hardened():
    settings = Settings(_env_file=None, **production_settings())
    assert settings.session_cookie_secure is True
    assert settings.cors_origin_list == ["https://legalease.example.com"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"secret_key": "legalease-development-key-change-me"},
        {"secret_key": "short"},
        {"session_cookie_secure": False},
        {"cors_origins": ""},
        {"cors_origins": "http://localhost:3000"},
        {"cors_origins": "http://127.0.0.1:3000"},
        {"ai_provider": "mock", "gemini_api_key": None},
    ],
)
def test_production_settings_reject_unsafe_configuration(overrides: dict[str, object]):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **production_settings(**overrides))


def test_production_rejects_the_development_only_mock_provider():
    with pytest.raises(ValidationError, match="development-only stub"):
        Settings(_env_file=None, **production_settings(ai_provider="mock", gemini_api_key=None))


def test_development_allows_the_mock_provider():
    settings = Settings(_env_file=None, app_env="development", ai_provider="mock")
    assert settings.is_development_ai is True


def test_development_defaults_are_unaffected():
    settings = Settings(_env_file=None, app_env="development", secret_key="dev", session_cookie_secure=False)
    assert settings.session_cookie_secure is False
