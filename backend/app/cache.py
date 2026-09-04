import json
import logging
from typing import Any

import redis

from app.config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None
_memory: dict[str, str] = {}
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
    client = get_redis()
    try:
        raw = client.get(key) if client else _memory.get(key)
    except Exception:  # noqa: BLE001
        raw = _memory.get(key)
    if not raw:
        return None
    return json.loads(raw)


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    payload = json.dumps(value)
    client = get_redis()
    ttl = ttl or settings.cache_ttl_seconds
    _memory[key] = payload
    if not client:
        return
    try:
        client.setex(key, ttl, payload)
    except Exception:  # noqa: BLE001
        pass
