from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "LegalEase"
    app_env: Literal["development", "test", "production"] = "development"
    secret_key: str = "legalease-development-key-change-me"
    database_url: str = "sqlite:///./legalease.db"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    ai_provider: Literal["mock", "gemini"] = "mock"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_timeout_seconds: float = Field(default=45.0, gt=0, le=300)
    gemini_max_attempts: int = Field(default=3, ge=1, le=6)
    gemini_retry_base_seconds: float = Field(default=2.0, ge=0, le=30)
    gemini_max_input_chars: int = Field(default=60000, gt=0, le=200000)

    session_cookie_name: str = "le_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_max_age: int = Field(default=604800, gt=0, le=2592000)
    csrf_cookie_name: str = "le_csrf"
    max_upload_mb: int = Field(default=10, ge=1, le=50)
    max_findings_per_review: int = Field(default=14, ge=1, le=40)
    max_clauses_per_review: int = Field(default=60, ge=5, le=200)
    max_review_questions_per_hour: int = Field(default=40, ge=5, le=500)
    max_review_rounds: int = Field(default=25, ge=2, le=100)
    admin_emails: str = ""

    @field_validator("cors_origins", "admin_emails", mode="before")
    @classmethod
    def split_values(cls, value: object) -> str:
        if isinstance(value, list):
            return ",".join(str(item) for item in value)
        return str(value or "")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> str:
        url = str(value or "")
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        return url

    @model_validator(mode="after")
    def validate_cookie_policy(self) -> "Settings":
        if self.session_cookie_samesite == "none" and not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SAMESITE=none requires SESSION_COOKIE_SECURE=true.")
        return self

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env != "production":
            return self
        if len(self.secret_key) < 32 or self.secret_key == "legalease-development-key-change-me":
            raise ValueError("APP_ENV=production requires a unique SECRET_KEY of at least 32 characters.")
        if not self.session_cookie_secure:
            raise ValueError("APP_ENV=production requires SESSION_COOKIE_SECURE=true.")
        origins = self.cors_origin_list
        if not origins:
            raise ValueError("APP_ENV=production requires at least one CORS_ORIGINS entry.")
        local_origins = {"http://localhost:3000", "http://127.0.0.1:3000"}
        if local_origins.intersection(origins):
            raise ValueError("APP_ENV=production must not keep local frontend origins in CORS_ORIGINS.")
        if self.ai_provider != "gemini":
            raise ValueError(
                "APP_ENV=production requires AI_PROVIDER=gemini. The mock provider is a "
                "development-only stub and must never serve production analysis."
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def admin_email_list(self) -> list[str]:
        return [item.strip().lower() for item in self.admin_emails.split(",") if item.strip()]

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_model)

    @property
    def is_development_ai(self) -> bool:
        """True when the deterministic development provider is active."""

        return self.ai_provider == "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
