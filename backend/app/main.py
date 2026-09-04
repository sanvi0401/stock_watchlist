from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import Base, engine
from app.errors import unhandled_exception_handler
from app.routers import auth, changes, dashboard, settings as settings_router, stocks, watchlists
from app.worker import start_scheduler

app = FastAPI(title=settings.app_name, version="1.0.0")
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
    Base.metadata.create_all(bind=engine)
    start_scheduler(settings.snapshot_refresh_seconds)


@app.get("/health")
def health() -> dict:
    from app.cache import get_redis, redis_available

    redis_ok = bool(get_redis()) or not redis_available
    return {"ok": True, "redis": "up" if get_redis() else "fallback", "cache_ok": redis_ok}


app.include_router(auth.router)
app.include_router(watchlists.router)
app.include_router(dashboard.router)
app.include_router(stocks.router)
app.include_router(changes.router)
app.include_router(settings_router.router)
