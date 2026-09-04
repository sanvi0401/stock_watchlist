"""Market-hours and quote-freshness rules, per exchange.

One place decides what LIVE / DELAYED / STALE mean and whether a market is
open, so every provider and every response uses the same definition.

Market state comes from, in order of preference:
1. the instrument's own regular-session window reported by the provider
   (Yahoo's currentTradingPeriod). If that window is not today's date in the
   exchange's timezone, the exchange is closed today: weekend *or holiday*.
2. a fallback table of regular hours keyed by Yahoo exchange code.
3. the US regular session.

- LIVE       : provider says real-time and the print is a few minutes old
- DELAYED    : delayed feed (Yahoo is ~15 min) but current for the session;
               also any quote while that market is closed
- STALE      : market is open and the newest print is older than the stale
               threshold, or a fallback snapshot is being served because the
               provider failed
- UNAVAILABLE: no valid quote at all
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import settings


@dataclass(frozen=True)
class ExchangeInfo:
    code: str
    name: str
    timezone: str
    open: time
    close: time
    currency: str


US = ExchangeInfo("NMS", "Nasdaq", "America/New_York", time(9, 30), time(16, 0), "USD")
NSE = ExchangeInfo("NSI", "NSE", "Asia/Kolkata", time(9, 15), time(15, 30), "INR")

# Regular sessions by Yahoo exchange code. Lunch breaks are ignored.
EXCHANGES: dict[str, ExchangeInfo] = {
    "NSI": NSE,
    "BSE": ExchangeInfo("BSE", "BSE", "Asia/Kolkata", time(9, 15), time(15, 30), "INR"),
    "NMS": US,
    "NGM": ExchangeInfo("NGM", "NasdaqGM", "America/New_York", time(9, 30), time(16, 0), "USD"),
    "NCM": ExchangeInfo("NCM", "NasdaqCM", "America/New_York", time(9, 30), time(16, 0), "USD"),
    "NYQ": ExchangeInfo("NYQ", "NYSE", "America/New_York", time(9, 30), time(16, 0), "USD"),
    "PCX": ExchangeInfo("PCX", "NYSEArca", "America/New_York", time(9, 30), time(16, 0), "USD"),
    "ASE": ExchangeInfo("ASE", "NYSE American", "America/New_York", time(9, 30), time(16, 0), "USD"),
    "BTS": ExchangeInfo("BTS", "Cboe BZX", "America/New_York", time(9, 30), time(16, 0), "USD"),
    "TOR": ExchangeInfo("TOR", "Toronto", "America/Toronto", time(9, 30), time(16, 0), "CAD"),
    "LSE": ExchangeInfo("LSE", "LSE", "Europe/London", time(8, 0), time(16, 30), "GBP"),
    "IOB": ExchangeInfo("IOB", "LSE IOB", "Europe/London", time(8, 0), time(16, 30), "USD"),
    "GER": ExchangeInfo("GER", "XETRA", "Europe/Berlin", time(9, 0), time(17, 30), "EUR"),
    "FRA": ExchangeInfo("FRA", "Frankfurt", "Europe/Berlin", time(8, 0), time(20, 0), "EUR"),
    "PAR": ExchangeInfo("PAR", "Paris", "Europe/Paris", time(9, 0), time(17, 30), "EUR"),
    "AMS": ExchangeInfo("AMS", "Amsterdam", "Europe/Amsterdam", time(9, 0), time(17, 30), "EUR"),
    "MIL": ExchangeInfo("MIL", "Milan", "Europe/Rome", time(9, 0), time(17, 30), "EUR"),
    "EBS": ExchangeInfo("EBS", "Swiss", "Europe/Zurich", time(9, 0), time(17, 30), "CHF"),
    "JPX": ExchangeInfo("JPX", "Tokyo", "Asia/Tokyo", time(9, 0), time(15, 30), "JPY"),
    "HKG": ExchangeInfo("HKG", "HKEX", "Asia/Hong_Kong", time(9, 30), time(16, 0), "HKD"),
    "SHH": ExchangeInfo("SHH", "Shanghai", "Asia/Shanghai", time(9, 30), time(15, 0), "CNY"),
    "SHZ": ExchangeInfo("SHZ", "Shenzhen", "Asia/Shanghai", time(9, 30), time(15, 0), "CNY"),
    "KSC": ExchangeInfo("KSC", "KOSPI", "Asia/Seoul", time(9, 0), time(15, 30), "KRW"),
    "SES": ExchangeInfo("SES", "SGX", "Asia/Singapore", time(9, 0), time(17, 0), "SGD"),
    "ASX": ExchangeInfo("ASX", "ASX", "Australia/Sydney", time(10, 0), time(16, 0), "AUD"),
    "SAO": ExchangeInfo("SAO", "B3", "America/Sao_Paulo", time(10, 0), time(17, 0), "BRL"),
}

# Yahoo symbol suffix -> exchange code, for providers that do not report one.
SUFFIX_EXCHANGE = {
    ".NS": "NSI", ".BO": "BSE", ".L": "LSE", ".DE": "GER", ".F": "FRA", ".PA": "PAR", ".AS": "AMS",
    ".MI": "MIL", ".SW": "EBS", ".T": "JPX", ".HK": "HKG", ".SS": "SHH", ".SZ": "SHZ", ".KS": "KSC",
    ".SI": "SES", ".AX": "ASX", ".SA": "SAO", ".TO": "TOR",
}


def exchange_for(code: str | None, symbol: str = "") -> ExchangeInfo:
    if code and code.upper() in EXCHANGES:
        return EXCHANGES[code.upper()]
    upper = (symbol or "").upper()
    for suffix, exch in SUFFIX_EXCHANGE.items():
        if upper.endswith(suffix):
            return EXCHANGES[exch]
    return US


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite drops tzinfo; normalise everything to aware UTC before comparing."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _zone(name: str | None, default: str) -> ZoneInfo:
    try:
        return ZoneInfo(name or default)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(default)


def market_state(
    now: datetime | None = None,
    *,
    exchange: str | None = None,
    symbol: str = "",
    timezone: str | None = None,
    session_start: datetime | None = None,
    session_end: datetime | None = None,
) -> str:
    """OPEN / PRE_MARKET / CLOSED for the exchange an instrument trades on."""
    now = as_utc(now) or datetime.now(UTC)
    info = exchange_for(exchange, symbol)
    tz = _zone(timezone, info.timezone)
    local = now.astimezone(tz)

    start, end = as_utc(session_start), as_utc(session_end)
    if start and end and end > start:
        if start.astimezone(tz).date() != local.date():
            return "CLOSED"  # provider's next session is another day: weekend or holiday
        if now < start:
            return "PRE_MARKET"
        return "OPEN" if now < end else "CLOSED"

    if local.weekday() >= 5:
        return "CLOSED"
    if local.time() < info.open:
        return "PRE_MARKET"
    return "OPEN" if local.time() < info.close else "CLOSED"


def classify_freshness(
    quoted_at: datetime,
    provider_status: str,
    *,
    now: datetime | None = None,
    fallback: bool = False,
    state: str | None = None,
) -> str:
    now = as_utc(now) or datetime.now(UTC)
    quoted_at = as_utc(quoted_at) or now
    if provider_status == "UNAVAILABLE":
        return "UNAVAILABLE"
    if fallback:
        return "STALE"
    state = state or market_state(now)
    age = now - quoted_at
    if state != "OPEN":
        # Nothing new can print while closed; the last session's close is current.
        return "LIVE" if provider_status == "LIVE" and age <= timedelta(minutes=5) else "DELAYED"
    if age > timedelta(minutes=settings.stale_after_minutes):
        return "STALE"
    if provider_status == "LIVE" and age <= timedelta(minutes=5):
        return "LIVE"
    return "DELAYED"


def session_timestamp(
    bar_date: datetime, now: datetime | None = None, *, exchange: str | None = None, symbol: str = "", timezone: str | None = None
) -> datetime:
    """Timestamp to attach to a daily bar when the provider gives no print time.

    Daily providers stamp a bar with the session's date or open, not the time
    of the last print. If the bar is for today's session it is still being
    updated, so the print is as fresh as the fetch. Otherwise the bar is final
    and its print time is that session's close.
    """
    now = as_utc(now) or datetime.now(UTC)
    info = exchange_for(exchange, symbol)
    tz = _zone(timezone, info.timezone)
    bar_local = (as_utc(bar_date) or now).astimezone(tz)
    if bar_local.date() >= now.astimezone(tz).date():
        return now
    return datetime.combine(bar_local.date(), info.close, tzinfo=tz).astimezone(UTC)


def major_markets(now: datetime | None = None) -> list[dict]:
    """Headline exchanges for the sidebar: NSE (home market) and US."""
    return [
        {"exchange": NSE.code, "exchange_name": NSE.name, "state": market_state(now, exchange=NSE.code)},
        {"exchange": "NYQ", "exchange_name": "NYSE / Nasdaq", "state": market_state(now, exchange="NYQ")},
    ]
