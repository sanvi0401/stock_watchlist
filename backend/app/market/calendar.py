from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# Approximate US equity holidays (weekday closures). Not a full exchange calendar feed.
_US_HOLIDAYS = {
    (1, 1),
    (1, 19),
    (2, 16),
    (4, 3),
    (5, 25),
    (6, 19),
    (7, 3),
    (9, 7),
    (11, 26),
    (12, 25),
}


def us_equity_session(now: datetime | None = None) -> str:
    """Return PRE, OPEN, CLOSED. Weekends/holidays are CLOSED. No LIVE pretence."""
    moment = now.astimezone(ET) if now else datetime.now(ET)
    if moment.weekday() >= 5:
        return "CLOSED"
    if (moment.month, moment.day) in _US_HOLIDAYS:
        return "CLOSED"
    open_t = time(9, 30)
    close_t = time(16, 0)
    t = moment.time()
    if t < open_t:
        return "PRE"
    if t >= close_t:
        return "CLOSED"
    return "OPEN"


def session_elapsed_fraction(now: datetime | None = None) -> float:
    """0–1 through the regular session. 1.0 when closed after the bell; 0 before open."""
    state = us_equity_session(now)
    if state == "CLOSED":
        moment = (now or datetime.now(UTC)).astimezone(ET)
        if moment.time() >= time(16, 0):
            return 1.0
        return 0.0
    if state == "PRE":
        return 0.0
    moment = (now or datetime.now(UTC)).astimezone(ET)
    start = moment.replace(hour=9, minute=30, second=0, microsecond=0)
    end = moment.replace(hour=16, minute=0, second=0, microsecond=0)
    total = (end - start).total_seconds()
    done = (moment - start).total_seconds()
    return max(0.0, min(1.0, done / total))


def classify_quote_status(provider_status: str, timestamp: datetime, now: datetime | None = None) -> str:
    from app.config import settings

    moment = now or datetime.now(UTC)
    ts = timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    age = (moment - ts.astimezone(UTC)).total_seconds()
    if provider_status == "UNAVAILABLE":
        return "UNAVAILABLE"
    if age < 0:
        age = 0
    if age <= settings.live_max_age_seconds and provider_status == "LIVE":
        return "LIVE"
    if age <= settings.delayed_max_age_seconds:
        return "DELAYED" if provider_status != "LIVE" or age > settings.live_max_age_seconds else "LIVE"
    if age <= settings.stale_max_age_seconds:
        return "STALE"
    return "STALE"
