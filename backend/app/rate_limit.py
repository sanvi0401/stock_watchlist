"""Per-IP fixed-window limit for credential endpoints, backed by the quote cache tier."""

from __future__ import annotations

import time

from fastapi import Request

from app.cache import cache_get, cache_set
from app.config import settings
from app.errors import AppError


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def auth_rate_limit(request: Request) -> None:
    limit = settings.auth_rate_limit_per_minute
    if limit <= 0 or settings.environment.lower() == "test":
        return
    window = int(time.time() // 60)
    key = f"rl:auth:{_client_ip(request)}:{window}"
    count = int(cache_get(key) or 0)
    if count >= limit:
        raise AppError(429, "rate_limited", "Too many attempts. Wait a minute and try again.")
    cache_set(key, count + 1, ttl=90)
