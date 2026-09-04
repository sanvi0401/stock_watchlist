import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import Base, engine
from app.errors import unhandled_exception_handler
from app.routers import auth, changes, dashboard, settings as settings_router, stocks, watchlists
from app.schemas import HealthOut
from app.worker import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.is_production and settings.secret_key == "dev-change-me-in-production":
        raise RuntimeError("SECRET_KEY must be set in production.")
    if settings.persistence_mode == "ephemeral":
        logger.warning("Persistence is EPHEMERAL (SQLite in /tmp). Set DATABASE_URL for durable storage.")
    if not os.getenv("VERCEL"):
        start_scheduler(settings.snapshot_refresh_seconds)
    yield
    stop_scheduler()


app = FastAPI(title=settings.app_name, version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.exception_handler(HTTPException)
async def http_exc(_request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(status_code=exc.status_code, content={"code": "error", "message": str(detail)})


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    from app.cache import get_redis
    from app.market.freshness import market_state
    from app.market.service import market_service

    return HealthOut(
        environment=settings.environment,
        provider=market_service.provider_name,
        cache="redis" if get_redis() else "memory",
        persistence=settings.persistence_mode,
        market_state=market_state(),
        server_time=datetime.now(UTC),
    )


app.include_router(auth.router)
app.include_router(watchlists.router)
app.include_router(dashboard.router)
app.include_router(stocks.router)
app.include_router(changes.router)
app.include_router(settings_router.router)
