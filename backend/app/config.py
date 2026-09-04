import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[1]


def _default_database_url() -> str:
    # Zero-setup local default. Postgres is opt-in through DATABASE_URL.
    if os.getenv("VERCEL"):
        return "sqlite+pysqlite:////tmp/marketwatch.db"
    return f"sqlite+pysqlite:///{_BACKEND_DIR / 'marketwatch.db'}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Smart Market Watch"
    environment: str = "development"
    secret_key: str = "dev-change-me-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7
    database_url: str = _default_database_url()
    redis_url: str = "redis://127.0.0.1:6379/0"
    cors_origins: str = "http://127.0.0.1:43123,http://localhost:43123"
    market_data_provider: str = "yfinance"
    alpha_vantage_api_key: str = ""
    cache_ttl_seconds: int = 60
    snapshot_refresh_seconds: int = 120
    # A dashboard load within this window counts as the same "visit": the
    # comparison baseline is not rolled forward, so refreshing does not
    # erase what changed since the previous visit.
    check_session_minutes: int = 10
    # While the market is open, a quote older than this is STALE.
    stale_after_minutes: int = 20
    max_symbols_per_watchlist: int = 100
    public_app_url: str = "http://127.0.0.1:43123"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def show_reset_link(self) -> bool:
        # No SMTP in this project. Outside production the reset link is
        # returned in the response so the flow can be exercised end to end.
        return not self.is_production

    @property
    def persistence_mode(self) -> str:
        if self.database_url.startswith("sqlite") and "/tmp/" in self.database_url:
            return "ephemeral"
        return "durable"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        for var in ("VERCEL_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
            host = os.getenv(var)
            if host:
                origins.append(f"https://{host}")
        return origins or ["http://127.0.0.1:43123"]

    @property
    def public_url(self) -> str:
        vercel = os.getenv("VERCEL_URL")
        if vercel:
            host = vercel if vercel.startswith("http") else f"https://{vercel}"
            return host.rstrip("/")
        return (self.public_app_url or "http://127.0.0.1:43123").rstrip("/")


settings = Settings()
