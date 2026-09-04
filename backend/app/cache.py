"""Latest-quote cache: Redis when reachable, otherwise an in-process TTL map.

Both tiers honour the TTL. The in-memory fallback previously never expired,
which froze prices for the life of the process whenever Redis was down.
"""

import json
import logging
import time
from threading import Lock
from typing import Any

import redis

from app.config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None
_memory: dict[str, tuple[float, str]] = {}
_memory_lock = Lock()
redis_available = True


def get_redis() -> redis.Redis | None:
    global _client, redis_available
    if not redis_available:
        return None
    if _client is None:
        try:
            _client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1)
            _client.ping()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis unavailable, using in-memory cache: %s", exc)
            redis_available = False
            _client = None
    return _client


def _memory_get(key: str) -> str | None:
    now = time.monotonic()
    with _memory_lock:
        entry = _memory.get(key)
        if not entry:
            return None
        expires_at, raw = entry
        if expires_at <= now:
            _memory.pop(key, None)
            return None
        return raw


def _memory_set(key: str, raw: str, ttl: int) -> None:
    with _memory_lock:
        _memory[key] = (time.monotonic() + ttl, raw)


def cache_get(key: str) -> Any | None:
    client = get_redis()
    raw: str | None = None
    if client:
        try:
            raw = client.get(key)
        except Exception:  # noqa: BLE001
            raw = None
    if raw is None:
        raw = _memory_get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    payload = json.dumps(value)
    ttl = ttl or settings.cache_ttl_seconds
    _memory_set(key, payload, ttl)
    client = get_redis()
    if not client:
        return
    try:
        client.setex(key, ttl, payload)
    except Exception:  # noqa: BLE001
        pass


def cache_delete(key: str) -> None:
    with _memory_lock:
        _memory.pop(key, None)
    client = get_redis()
    if client:
        try:
            client.delete(key)
        except Exception:  # noqa: BLE001
            pass
