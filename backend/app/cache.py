import json
import logging
import time
from typing import Any

import redis

from app.config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None
_memory: dict[str, tuple[str, float]] = {}
redis_available = True


def get_redis() -> redis.Redis | None:
    global _client, redis_available
    if not redis_available:
        return None
    if _client is None:
        try:
            _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            _client.ping()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis unavailable, using in-memory cache: %s", exc)
            redis_available = False
            _client = None
    return _client


def cache_get(key: str) -> Any | None:
    now = time.time()
    mem = _memory.get(key)
    if mem:
        payload, expires = mem
        if expires < now:
            _memory.pop(key, None)
        else:
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                _memory.pop(key, None)
    client = get_redis()
    try:
        raw = client.get(key) if client else None
    except Exception:  # noqa: BLE001
        raw = None
    if not raw:
        return None
    return json.loads(raw)


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    payload = json.dumps(value)
    ttl = int(ttl or settings.cache_ttl_seconds)
    _memory[key] = (payload, time.time() + max(ttl, 1))
    client = get_redis()
    if not client:
        return
    try:
        client.setex(key, ttl, payload)
    except Exception:  # noqa: BLE001
        pass


def cache_delete(key: str) -> None:
    _memory.pop(key, None)
    client = get_redis()
    if not client:
        return
    try:
        client.delete(key)
    except Exception:  # noqa: BLE001
        pass
