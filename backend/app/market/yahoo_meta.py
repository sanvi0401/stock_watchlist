"""Shared Yahoo helpers used by both the httpx and yfinance providers: metadata parsing,
the previous-close rule for daily bars, and symbol search."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

logger = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
SEARCH_TYPES = {"", "EQUITY", "ETF", "INDEX", "MUTUALFUND"}


def _epoch(value: Any) -> datetime | None:
    try:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if hasattr(value, "to_pydatetime"):
            dt = value.to_pydatetime()
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def exchange_context(meta: dict) -> dict:
    """currency / exchange / timezone / regular session / print time from Yahoo meta."""
    regular = ((meta.get("currentTradingPeriod") or {}).get("regular")) or {}
    name = str(meta.get("longName") or meta.get("shortName") or "").strip()
    return {
        "company_name": name,
        "currency": str(meta.get("currency") or ""),
        "exchange": str(meta.get("exchangeName") or ""),
        "exchange_name": str(meta.get("fullExchangeName") or meta.get("exchangeName") or ""),
        "timezone": str(meta.get("exchangeTimezoneName") or ""),
        "session_start": _epoch(regular.get("start")),
        "session_end": _epoch(regular.get("end")),
        "print_time": _epoch(meta.get("regularMarketTime")),
    }


def get(meta: Any, key: str, default: Any = None) -> Any:
    """yfinance exposes metadata as a dict-like object, not a dict."""
    try:
        value = meta.get(key, default) if hasattr(meta, "get") else default
    except Exception:  # noqa: BLE001
        return default
    return default if value is None else value


def previous_close(
    bars: list[tuple[datetime, float]], print_time: datetime | None, timezone: str | None
) -> float | None:
    """The close of the last *finished* session.

    ``bars`` are (bar time, close) with NaN/None closes already removed. If the
    newest bar is for the same local date as the print, it is today's session
    (finished or still running) and the previous close is the bar before it.
    Otherwise today's bar has not appeared yet and the newest bar *is* the
    previous close.
    """
    if not bars:
        return None
    try:
        tz = ZoneInfo(timezone or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        tz = UTC
    last_time, last_close = bars[-1]
    if print_time is not None:
        last_local = (last_time if last_time.tzinfo else last_time.replace(tzinfo=UTC)).astimezone(tz).date()
        print_local = (print_time if print_time.tzinfo else print_time.replace(tzinfo=UTC)).astimezone(tz).date()
        if last_local < print_local:
            return last_close
    return bars[-2][1] if len(bars) > 1 else last_close


def search_rows(query: str, limit: int = 8, client: httpx.Client | None = None) -> list[dict]:
    """Yahoo symbol search across every exchange it covers: [{symbol, name, exchange, exchange_name}]."""
    q = (query or "").strip()
    if not q:
        return []
    own = client is None
    client = client or httpx.Client(timeout=8.0, headers={"User-Agent": _UA, "Accept": "application/json"})
    try:
        resp = client.get(SEARCH_URL, params={"q": q, "quotesCount": max(limit, 10), "newsCount": 0})
        resp.raise_for_status()
        rows = resp.json().get("quotes") or []
    except Exception:  # noqa: BLE001
        logger.warning("yahoo search failed for %r", q, exc_info=True)
        rows = []
    finally:
        if own:
            client.close()
    out: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        symbol = str(row.get("symbol") or "").upper()
        if not symbol or symbol in seen or str(row.get("quoteType") or "").upper() not in SEARCH_TYPES:
            continue
        seen.add(symbol)
        out.append(
            {
                "symbol": symbol,
                "name": str(row.get("longname") or row.get("shortname") or symbol),
                "exchange": str(row.get("exchange") or ""),
                "exchange_name": str(row.get("exchDisp") or ""),
            }
        )
        if len(out) >= limit:
            break
    return out
