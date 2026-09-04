from time import time

from fastapi import Request

from app.cache import cache_get, cache_set
from app.config import settings
from app.errors import AppError

_AUTH_PATHS = {
    "/auth/login",
    "/auth/register",
    "/auth/forgot-password",
    "/auth/reset-password",
}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_auth_rate_limit(request: Request) -> None:
    if settings.environment == "test":
        return
    path = request.url.path
    if path not in _AUTH_PATHS and not path.endswith(tuple(_AUTH_PATHS)):
        # mounted without prefix sometimes
        if not any(path.endswith(p) for p in _AUTH_PATHS):
            return
    ip = _client_ip(request)
    window = int(time() // 60)
    key = f"rl:{ip}:{path}:{window}"
    count = int(cache_get(key) or 0)
    limit = settings.auth_rate_limit_per_minute
    if count >= limit:
        raise AppError(429, "rate_limited", "Too many attempts. Wait a minute and try again.")
    cache_set(key, count + 1, ttl=70)


def rate_limit_dependency(request: Request) -> None:
    enforce_auth_rate_limit(request)
