"""Per-instance provider cooldown. Shared across requests on one process; Redis if available."""

from __future__ import annotations

import time

from app.cache import cache_get, cache_set

_KEY = "provider:cooldown"
_DEFAULT_SECONDS = 30
_MAX_SECONDS = 300


class ProviderLimited(Exception):
    def __init__(self, retry_after: int = 30) -> None:
        super().__init__("market provider rate-limited")
        self.retry_after = retry_after


def is_cooling_down() -> bool:
    row = cache_get(_KEY)
    if not row:
        return False
    until = float(row.get("until") or 0)
    return time.time() < until


def note_failure(status_code: int | None = None, retry_after: int | None = None) -> None:
    wait = retry_after or _DEFAULT_SECONDS
    if status_code == 429:
        wait = max(wait, 60)
    wait = min(wait * 2 if cache_get(_KEY) else wait, _MAX_SECONDS)
    cache_set(_KEY, {"until": time.time() + wait, "code": status_code}, ttl=wait)


def note_success() -> None:
    cache_set(_KEY, {"until": 0}, ttl=1)
