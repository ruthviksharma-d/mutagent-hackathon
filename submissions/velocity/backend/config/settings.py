"""
Centralized application configuration.
Reads values from environment variables / .env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "PromptShield AI"
    ENVIRONMENT: str = "development"

    # --- Database ---
    DATABASE_URL: str = ""
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "promptshield"
    DB_USER: str = "root"
    DB_PASSWORD: str = "changeme"

    # --- Auth ---
    # This default is intentionally an obviously-insecure placeholder, not
    # a "real" secret - see main.py's startup check, which refuses to boot
    # with ENVIRONMENT=production while this default is still in place.
    JWT_SECRET_KEY: str = "insecure-dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CORS ---
    # Browser extension requests come from the background service worker
    # (chrome-extension:// origin with host_permissions granted in
    # manifest.json), which Chrome does not subject to page-origin CORS
    # enforcement the way a content-script/page-context fetch would be -
    # so no chrome-extension:// entry is needed or meaningful here. This
    # list only needs to cover browser-page origins: the admin dashboard's
    # dev and preview ports.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:4173"

    # --- Rate limiting (Milestone 6 hardening) ---
    # In-memory, single-instance limiter for the unauthenticated auth
    # endpoints (login/register are the only endpoints an attacker can hit
    # without a valid JWT). A multi-instance deployment would need this
    # backed by a shared store (e.g. Redis) instead - out of scope for
    # this MVP's "no Redis" constraint, called out in docs/BUSINESS_MODEL.md.
    AUTH_RATE_LIMIT_MAX_ATTEMPTS: int = 10
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # --- AI (future milestones) ---
    OPENROUTER_API_KEY: str = ""

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        from urllib.parse import quote_plus
        escaped_password = quote_plus(self.DB_PASSWORD) if self.DB_PASSWORD else ""
        return (
            f"mysql+pymysql://{self.DB_USER}:{escaped_password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
