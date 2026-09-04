import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_database_url() -> str:
    if os.getenv("VERCEL"):
        return "sqlite+pysqlite:////tmp/marketwatch.db"
    return "postgresql+psycopg2://marketwatch:marketwatch@127.0.0.1:5432/marketwatch"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Market Watch"
    environment: str = "development"
    secret_key: str = "dev-change-me-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7
    database_url: str = _default_database_url()
    redis_url: str = "redis://127.0.0.1:6379/0"
    cors_origins: str = "http://127.0.0.1:43123,http://localhost:43123"
    market_data_provider: str = "mock"
    alpha_vantage_api_key: str = ""
    cache_ttl_seconds: int = 60
    snapshot_refresh_seconds: int = 120
    public_app_url: str = "http://127.0.0.1:43123"

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


settings = Settings()
