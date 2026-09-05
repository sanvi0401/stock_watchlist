import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings, validate_settings
from app.db import Base, engine, ensure_detected_change_columns
from app.errors import AppError, unhandled_exception_handler
from app.market.calendar import us_equity_session
from app.routers import auth, changes, dashboard, settings as settings_router, stocks, watchlists
from app.worker import refresh_watched_symbols, start_scheduler

app = FastAPI(title=settings.app_name, version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
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


@app.on_event("startup")
def on_startup() -> None:
    validate_settings(settings)
    Base.metadata.create_all(bind=engine)
    ensure_detected_change_columns()
    if not os.getenv("VERCEL"):
        start_scheduler(settings.snapshot_refresh_seconds)


@app.get("/health")
def health() -> dict:
    from app.cache import get_redis, redis_available

    redis_ok = bool(get_redis()) or not redis_available
    return {
        "ok": True,
        "redis": "up" if get_redis() else "fallback",
        "cache_ok": redis_ok,
        "environment": settings.environment,
        "provider": settings.market_data_provider,
        "refresh": "background-scheduler" if not os.getenv("VERCEL") else "request-driven",
    }


@app.get("/market/session")
def market_session() -> dict:
    state = us_equity_session()
    return {
        "market_state": state,
        "exchange": "US equities (regular hours approximation, not a full holiday feed)",
    }


@app.post("/internal/refresh-snapshots")
def cron_refresh(x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret")) -> dict:
    if not settings.cron_secret:
        raise AppError(404, "not_found", "Cron refresh is not configured.")
    if not x_cron_secret or x_cron_secret != settings.cron_secret:
        raise AppError(401, "unauthorized", "Invalid cron secret.")
    refresh_watched_symbols()
    return {"ok": True}


app.include_router(auth.router)
app.include_router(watchlists.router)
app.include_router(dashboard.router)
app.include_router(stocks.router)
app.include_router(changes.router)
app.include_router(settings_router.router)
