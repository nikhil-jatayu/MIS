from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Application configuration. Every value can be overridden through .env."""

    model_config = SettingsConfigDict(
        env_file=(str(ROOT_DIR / ".env"), str(BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "JES MIS"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(default="postgresql+psycopg://postgres:postgres@localhost:5432/MIS")
    test_database_url: str | None = None

    jwt_secret_key: str = "development-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    cors_origins: str = "http://localhost:3000"
    cookie_name: str = "jes_access_token"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cookie_domain: str | None = None

    upload_dir: str = "var/uploads"
    max_upload_size_mb: int = 20
    allowed_upload_extensions: str = (
        "pdf,png,jpg,jpeg,gif,webp,txt,csv,doc,docx,xls,xlsx,ppt,pptx,zip"
    )

    seed_on_startup: bool = True
    scheduler_enabled: bool = True
    scheduler_interval_minutes: int = 1440
    scheduler_timezone: str = "Asia/Kolkata"
    scheduler_run_on_startup: bool = False

    login_max_attempts: int = 10
    login_lock_minutes: int = 15
    password_min_length: int = 8
    bcrypt_rounds: int = 12

    default_page_size: int = 20
    max_page_size: int = 100

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        if not path.is_absolute():
            path = BACKEND_DIR / path
        return path.resolve()

    @property
    def allowed_extensions(self) -> set[str]:
        return {
            extension.strip().lower().lstrip(".")
            for extension in self.allowed_upload_extensions.split(",")
            if extension.strip()
        }

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.cookie_samesite not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be one of: lax, strict, none")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true when COOKIE_SAMESITE=none")
        if self.is_production and self.jwt_secret_key in {
            "development-only-secret-change-me",
            "CHANGE_ME_TO_A_LONG_RANDOM_SECRET",
        }:
            raise ValueError("JWT_SECRET_KEY must be changed in production")
        if self.access_token_expire_minutes < 5:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be at least 5")
        if not 4 <= self.bcrypt_rounds <= 16:
            raise ValueError("BCRYPT_ROUNDS must be between 4 and 16")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
