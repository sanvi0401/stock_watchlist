"""Market-hours and quote-freshness rules.

One place decides what LIVE / DELAYED / STALE mean, so every provider and
every response uses the same definition:

- LIVE       : provider says real-time and the print is a few minutes old
- DELAYED    : provider is a delayed feed (Yahoo is ~15 min) but current for
               the session; also any quote while the market is closed
- STALE      : market is open and the newest print is older than the stale
               threshold, or a fallback snapshot is being served because the
               provider failed
- UNAVAILABLE: no valid quote at all
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.config import settings

NY = ZoneInfo("America/New_York")
_OPEN = time(9, 30)
_CLOSE = time(16, 0)


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite drops tzinfo; normalise everything to aware UTC before comparing."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def market_state(now: datetime | None = None) -> str:
    """US regular session state. Exchange holidays are not modelled (documented limitation)."""
    now = as_utc(now) or datetime.now(UTC)
    local = now.astimezone(NY)
    if local.weekday() >= 5:
        return "CLOSED"
    t = local.time()
    if t < _OPEN:
        return "PRE_MARKET"
    if t >= _CLOSE:
        return "CLOSED"
    return "OPEN"


def classify_freshness(
    quoted_at: datetime,
    provider_status: str,
    *,
    now: datetime | None = None,
    fallback: bool = False,
) -> str:
    now = as_utc(now) or datetime.now(UTC)
    quoted_at = as_utc(quoted_at) or now
    if provider_status == "UNAVAILABLE":
        return "UNAVAILABLE"
    if fallback:
        return "STALE"
    state = market_state(now)
    age = now - quoted_at
    if state != "OPEN":
        # Nothing new can print while closed; the last session's close is current.
        return "DELAYED" if provider_status != "LIVE" or age > timedelta(minutes=5) else "LIVE"
    if age > timedelta(minutes=settings.stale_after_minutes):
        return "STALE"
    if provider_status == "LIVE" and age <= timedelta(minutes=5):
        return "LIVE"
    return "DELAYED"


def session_timestamp(bar_date: datetime, now: datetime | None = None) -> datetime:
    """Timestamp to attach to a daily bar.

    Daily providers stamp a bar with the session's date or open, not the time
    of the last print. If the bar is for today's session it is still being
    updated, so the print is as fresh as the fetch. Otherwise the bar is final
    and its print time is that session's close (16:00 ET).
    """
    now = as_utc(now) or datetime.now(UTC)
    bar_local = (as_utc(bar_date) or now).astimezone(NY)
    if bar_local.date() >= now.astimezone(NY).date():
        return now
    close_local = datetime.combine(bar_local.date(), _CLOSE, tzinfo=NY)
    return close_local.astimezone(UTC)
