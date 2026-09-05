import os
import sys

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

KNOWN_INSECURE_SECRETS = {
    "",
    "dev-change-me-in-production",
    "replace-with-a-long-random-string",
    "test-secret",
    "secret",
    "changeme",
}

LOCAL_DEV_SECRET = "local-dev-only-not-for-production-0001"


def _default_environment() -> str:
    explicit = (os.getenv("ENVIRONMENT") or "").strip().lower()
    if explicit:
        return explicit
    if os.getenv("VERCEL"):
        return "production"
    return "development"


def _default_database_url() -> str:
    env = _default_environment()
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL", "")
    if env in {"development", "test"}:
        return "sqlite+pysqlite:///./marketwatch.dev.db"
    return ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Market Watch"
    environment: str = _default_environment()
    secret_key: str = ""
    access_token_expire_minutes: int = 60 * 24
    database_url: str = _default_database_url()
    redis_url: str = "redis://127.0.0.1:6379/0"
    cors_origins: str = "http://127.0.0.1:43123,http://localhost:43123"
    market_data_provider: str = "yfinance"
    alpha_vantage_api_key: str = ""
    cache_ttl_seconds: int = 60
    snapshot_refresh_seconds: int = 120
    public_app_url: str = "http://127.0.0.1:43123"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    resend_api_key: str = ""
    email_from: str = ""
    live_max_age_seconds: int = 5 * 60
    delayed_max_age_seconds: int = 20 * 60
    stale_max_age_seconds: int = 24 * 60 * 60
    snapshot_retention_days: int = 14
    cron_secret: str = ""
    auth_rate_limit_per_minute: int = 20

    @model_validator(mode="after")
    def _dev_secret_if_empty(self):
        if self.environment in {"development", "test"} and not self.secret_key:
            self.secret_key = LOCAL_DEV_SECRET
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_dev_or_test(self) -> bool:
        return self.environment in {"development", "test"}

    @property
    def allow_dev_reset_echo(self) -> bool:
        if os.getenv("VERCEL"):
            return False
        return self.environment in {"development", "test"}

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        vercel_url = os.getenv("VERCEL_URL")
        if vercel_url:
            origins.append(f"https://{vercel_url}")
        prod = os.getenv("VERCEL_PROJECT_PRODUCTION_URL")
        if prod:
            origins.append(f"https://{prod}")
        return origins or ["http://127.0.0.1:43123"]

    @property
    def public_url(self) -> str:
        vercel = os.getenv("VERCEL_URL")
        if vercel:
            host = vercel if vercel.startswith("http") else f"https://{vercel}"
            return host.rstrip("/")
        return (self.public_app_url or "http://127.0.0.1:43123").rstrip("/")

    @property
    def frontend_origin(self) -> str:
        return self.public_url


def validate_settings(cfg: "Settings | None" = None) -> None:
    cfg = cfg or settings
    if not cfg.is_production:
        if not cfg.secret_key:
            cfg.secret_key = LOCAL_DEV_SECRET
        return
    if cfg.secret_key in KNOWN_INSECURE_SECRETS or len(cfg.secret_key) < 32:
        print(
            "FATAL: production requires SECRET_KEY of at least 32 characters "
            "and must not be a committed fallback.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    url = (cfg.database_url or "").lower()
    if not url or "/tmp/" in url or ":memory:" in url or "sqlite" in url:
        print(
            "FATAL: production requires a persistent DATABASE_URL "
            "(Postgres). Ephemeral SQLite is not allowed.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if not cfg.resend_api_key or not cfg.email_from:
        print(
            "FATAL: production requires RESEND_API_KEY and EMAIL_FROM for password reset email.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def get_settings() -> Settings:
    return settings


settings = Settings()
