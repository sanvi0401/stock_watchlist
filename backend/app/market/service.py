"""MarketDataService: one shared quote path for every user, on any exchange.

provider -> validate/normalise -> resolve conflicts with the stored snapshot ->
persist snapshot -> cache. Reads go cache -> provider -> last snapshot (STALE).
Snapshots are shared across users, so N users watching RELIANCE.NS cost one
fetch per refresh interval, not N.

Provider cooldown: after a provider failure the provider is skipped for
``provider_cooldown_seconds`` and stored snapshots are served as STALE. A
flapping or throttling upstream degrades the labels, not the product.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import cache_get, cache_set
from app.config import settings
from app.market.alpha_vantage import AlphaVantageProvider
from app.market.freshness import as_utc, classify_freshness, exchange_for, market_state
from app.market.mock import MockMarketDataProvider
from app.market.types import NormalizedQuote
from app.models import MarketSnapshot

logger = logging.getLogger(__name__)

PROVIDER_STATUSES = {"LIVE", "DELAYED", "UNAVAILABLE"}
PREFETCH_CHUNK = 50
_COOLDOWN_KEY = "provider:cooldown_until"

# Yahoo quotes some markets in minor units: pence, agorot, cents.
MINOR_UNIT_CURRENCIES = {"GBp": "GBP", "ILA": "ILS", "ZAc": "ZAR"}

# Search ranking: home market first, then the big US venues, then the rest.
EXCHANGE_RANK = {"NSI": 0, "NMS": 1, "NYQ": 1, "NGM": 1, "NCM": 1, "PCX": 1, "BSE": 2, "LSE": 3, "TOR": 3, "JPX": 3, "HKG": 3}


def _provider():
    name = (settings.market_data_provider or "yfinance").lower()
    if name == "alpha_vantage" and settings.alpha_vantage_api_key:
        return AlphaVantageProvider()
    if name == "mock":
        return MockMarketDataProvider()
    # Vercel cannot bundle pandas/yfinance under the function size cap.
    if os.getenv("VERCEL") or name in {"yahoo", "yahoo_http"}:
        from app.market.yahoo_http import YahooHttpProvider

        return YahooHttpProvider()
    from app.market.yfinance_provider import YFinanceProvider

    return YFinanceProvider()


def _validate(quote: NormalizedQuote | None) -> NormalizedQuote | None:
    """Reject malformed prints and normalise units. Providers return zeros, NaNs, naive
    timestamps, and prices in pence; none of that may reach scoring."""
    if quote is None:
        return None
    try:
        if not (quote.price > 0 and quote.previous_close > 0):
            return None
        if quote.price != quote.price or quote.previous_close != quote.previous_close:
            return None
    except TypeError:
        return None
    if quote.data_status not in PROVIDER_STATUSES:
        quote.data_status = "DELAYED"
    quote.timestamp = as_utc(quote.timestamp) or datetime.now(UTC)
    if quote.timestamp > datetime.now(UTC):
        quote.timestamp = datetime.now(UTC)  # a print from the future is a clock or parsing problem
    if quote.volume < 0:
        quote.volume = 0.0
    if quote.average_volume <= 0:
        quote.average_volume = quote.volume or 1.0
    if not (0 < quote.volatility < 1):
        quote.volatility = 0.02
    quote.symbol = quote.symbol.upper().strip()
    if quote.currency in MINOR_UNIT_CURRENCIES:
        for attr in ("price", "previous_close", "week_52_high", "week_52_low"):
            setattr(quote, attr, getattr(quote, attr) / 100.0)
        quote.sparkline = [x / 100.0 for x in quote.sparkline]
        quote.currency = MINOR_UNIT_CURRENCIES[quote.currency]
    info = exchange_for(quote.exchange, quote.symbol)
    quote.exchange = (quote.exchange or info.code).upper()
    quote.exchange_name = quote.exchange_name or info.name
    quote.timezone = quote.timezone or info.timezone
    quote.currency = (quote.currency or info.currency).upper()
    quote.session_start = as_utc(quote.session_start)
    quote.session_end = as_utc(quote.session_end)
    return quote


def _finalize(quote: NormalizedQuote, *, fallback: bool = False, now: datetime | None = None) -> NormalizedQuote:
    """Apply the time-dependent labels at read time; never trust a cached label."""
    now = now or datetime.now(UTC)
    quote.market_state = market_state(
        now,
        exchange=quote.exchange,
        symbol=quote.symbol,
        timezone=quote.timezone,
        session_start=quote.session_start,
        session_end=quote.session_end,
    )
    quote.data_status = classify_freshness(
        quote.timestamp, quote.data_status, now=now, fallback=fallback, state=quote.market_state
    )
    return quote


def persist_snapshot(db: Session, quote: NormalizedQuote) -> MarketSnapshot:
    snap = MarketSnapshot(
        symbol=quote.symbol,
        company_name=quote.company_name,
        price=quote.price,
        previous_close=quote.previous_close,
        volume=quote.volume,
        average_volume=quote.average_volume,
        volatility=quote.volatility,
        market_cap=quote.market_cap,
        week_52_high=quote.week_52_high,
        week_52_low=quote.week_52_low,
        sparkline=json.dumps(quote.sparkline or []),
        currency=quote.currency,
        exchange=quote.exchange,
        exchange_name=quote.exchange_name,
        timezone=quote.timezone,
        session_start=quote.session_start,
        session_end=quote.session_end,
        timestamp=quote.timestamp,
        source=quote.source,
        provider_status=quote.data_status,
    )
    db.add(snap)
    db.flush()
    return snap


def latest_db_snapshot(db: Session, symbol: str) -> MarketSnapshot | None:
    return db.scalar(
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol == symbol.upper())
        .order_by(MarketSnapshot.timestamp.desc(), MarketSnapshot.id.desc())
        .limit(1)
    )


def snapshot_to_quote(snap: MarketSnapshot) -> NormalizedQuote:
    try:
        spark = [float(x) for x in json.loads(snap.sparkline or "[]")]
    except (ValueError, TypeError):
        spark = []
    return NormalizedQuote(
        symbol=snap.symbol,
        company_name=snap.company_name,
        price=snap.price,
        previous_close=snap.previous_close,
        volume=snap.volume,
        average_volume=snap.average_volume,
        volatility=snap.volatility,
        market_cap=snap.market_cap,
        week_52_high=snap.week_52_high,
        week_52_low=snap.week_52_low,
        timestamp=as_utc(snap.timestamp) or datetime.now(UTC),
        source=snap.source,
        data_status=snap.provider_status,
        market_state="UNKNOWN",
        sparkline=spark,
        currency=snap.currency or "USD",
        exchange=snap.exchange or "",
        exchange_name=snap.exchange_name or "",
        timezone=snap.timezone or "",
        session_start=as_utc(snap.session_start),
        session_end=as_utc(snap.session_end),
    )


def _cache_key(symbol: str) -> str:
    return f"quote:{settings.market_data_provider}:{symbol}"


def _quote_from_cache(symbol: str) -> NormalizedQuote | None:
    cached = cache_get(_cache_key(symbol))
    if not cached:
        return None
    try:
        for key in ("timestamp", "session_start", "session_end"):
            if cached.get(key):
                cached[key] = datetime.fromisoformat(cached[key])
        return NormalizedQuote(**cached)
    except (KeyError, TypeError, ValueError):
        return None


def _cache_quote(quote: NormalizedQuote) -> None:
    payload = {
        **quote.__dict__,
        "timestamp": quote.timestamp.isoformat(),
        "session_start": quote.session_start.isoformat() if quote.session_start else None,
        "session_end": quote.session_end.isoformat() if quote.session_end else None,
    }
    cache_set(_cache_key(quote.symbol), payload, ttl=settings.cache_ttl_seconds)


def provider_cooldown_remaining() -> int:
    row = cache_get(_COOLDOWN_KEY)
    until = float(row.get("until", 0)) if isinstance(row, dict) else 0.0
    return max(0, int(until - time.time()))


def _note_provider_failure() -> None:
    ttl = settings.provider_cooldown_seconds
    if ttl > 0:
        cache_set(_COOLDOWN_KEY, {"until": time.time() + ttl}, ttl=ttl)


class MarketDataService:
    def __init__(self) -> None:
        self.provider = _provider()

    @property
    def provider_name(self) -> str:
        return getattr(self.provider, "source", type(self.provider).__name__)

    def _store(self, db: Session, symbol: str, fresh: NormalizedQuote | None) -> tuple[NormalizedQuote | None, MarketSnapshot | None]:
        """Persist a validated provider quote, resolving conflicts with what we already hold.

        Conflict rule: a snapshot never moves backwards in time. If the provider
        hands back an older print than the one stored (retry storms, a lagging
        replica, two providers), the stored one wins and is served.
        """
        existing = latest_db_snapshot(db, symbol)
        if fresh is None or fresh.data_status == "UNAVAILABLE":
            return None, existing
        if existing is not None:
            existing_ts = as_utc(existing.timestamp)
            if existing_ts and fresh.timestamp < existing_ts:
                logger.info("conflict: provider print for %s older than stored snapshot; keeping stored", symbol)
                kept = snapshot_to_quote(existing)
                _cache_quote(kept)
                return kept, existing
            if (
                existing.price == fresh.price
                and existing.previous_close == fresh.previous_close
                and existing.volume == fresh.volume
            ):
                # Nothing changed since the last fetch: refresh the row in place
                # instead of growing the table on every poll.
                existing.timestamp = fresh.timestamp
                existing.fetched_at = datetime.now(UTC)
                existing.provider_status = fresh.data_status
                existing.session_start = fresh.session_start
                existing.session_end = fresh.session_end
                db.flush()
                _cache_quote(fresh)
                return fresh, existing
        snap = persist_snapshot(db, fresh)
        _cache_quote(fresh)
        return fresh, snap

    def _fetch_one(self, symbol: str) -> NormalizedQuote | None:
        if provider_cooldown_remaining() > 0:
            return None
        try:
            return _validate(self.provider.get_quote(symbol))
        except Exception:  # noqa: BLE001
            logger.warning("provider get_quote failed for %s; cooling down", symbol, exc_info=True)
            _note_provider_failure()
            return None

    def get_quote(self, db: Session, symbol: str) -> tuple[NormalizedQuote | None, MarketSnapshot | None]:
        symbol = symbol.upper().strip()
        if not symbol:
            return None, None

        cached = _quote_from_cache(symbol)
        if cached:
            return _finalize(cached), latest_db_snapshot(db, symbol)

        fresh = self._fetch_one(symbol)
        quote, snap = self._store(db, symbol, fresh)
        if quote:
            return _finalize(quote), snap
        if snap:
            # Provider miss or cooldown: serve the last good print, labelled STALE, never as live.
            return _finalize(snapshot_to_quote(snap), fallback=True), snap
        if fresh is not None and fresh.data_status == "UNAVAILABLE":
            return _finalize(fresh), None
        return None, None

    def prefetch(self, db: Session, symbols: list[str]) -> None:
        """Batch-fetch everything not already cached. One provider call per chunk, shared by all users."""
        needed: list[str] = []
        seen: set[str] = set()
        for raw in symbols:
            symbol = raw.upper().strip()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            if _quote_from_cache(symbol) is None:
                needed.append(symbol)
        if needed and provider_cooldown_remaining() > 0:
            return
        for start in range(0, len(needed), PREFETCH_CHUNK):
            chunk = needed[start : start + PREFETCH_CHUNK]
            try:
                fetched = self.provider.get_quotes(chunk)
            except Exception:  # noqa: BLE001
                logger.warning("provider batch failed for %d symbols; cooling down", len(chunk), exc_info=True)
                _note_provider_failure()
                return
            for symbol in chunk:
                self._store(db, symbol, _validate(fetched.get(symbol)))

    def search(self, db: Session, query: str) -> list[NormalizedQuote]:
        """Provider search, ranked for this product: NSE first, then US, dedupe BSE twins."""
        from app.symbol_names import NAME_TO_SYMBOL

        try:
            results = self.provider.search(query)
        except Exception:  # noqa: BLE001
            results = []
        cleaned = [_finalize(q) for q in (_validate(item) for item in results) if q is not None]

        needle = (query or "").strip().lower()
        bases = {q.symbol.split(".")[0] for q in cleaned if q.symbol.endswith(".NS")}
        cleaned = [q for q in cleaned if not (q.symbol.endswith(".BO") and q.symbol.split(".")[0] in bases)]

        def rank(q: NormalizedQuote) -> tuple:
            name = q.company_name.lower()
            exact = 0 if needle and (needle == q.symbol.lower() or name.startswith(needle)) else 1
            return (exact, EXCHANGE_RANK.get(q.exchange, 5), q.symbol)

        cleaned.sort(key=rank)
        hint = NAME_TO_SYMBOL.get(needle)
        if hint:
            quoted, _ = self.get_quote(db, hint)
            if quoted:
                cleaned = [quoted] + [c for c in cleaned if c.symbol != quoted.symbol]
        return cleaned

    def refresh_symbols(self, db: Session, symbols: list[str]) -> None:
        self.prefetch(db, list(symbols))
        db.commit()


def prune_snapshots(db: Session, keep_days: int = 7) -> int:
    """Drop old snapshot rows, always keeping the newest row per symbol (it is the outage fallback)."""
    from sqlalchemy import delete, func

    cutoff = datetime.now(UTC) - timedelta(days=keep_days)
    newest = select(func.max(MarketSnapshot.id)).group_by(MarketSnapshot.symbol)
    result = db.execute(
        delete(MarketSnapshot).where(MarketSnapshot.fetched_at < cutoff, MarketSnapshot.id.not_in(newest))
    )
    db.commit()
    return result.rowcount or 0


market_service = MarketDataService()
