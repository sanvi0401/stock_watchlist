import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import cache_get, cache_set
from app.config import settings
from app.market.alpha_vantage import AlphaVantageProvider
from app.market.mock import MockMarketDataProvider
from app.market.types import NormalizedQuote
from app.models import MarketSnapshot

VALID_STATUSES = {"LIVE", "DELAYED", "STALE", "UNAVAILABLE"}


def _provider():
    name = (settings.market_data_provider or "yfinance").lower()
    if name == "alpha_vantage" and settings.alpha_vantage_api_key:
        return AlphaVantageProvider()
    if name == "mock":
        return MockMarketDataProvider()
    # Vercel cannot bundle pandas/yfinance under the 225 MB function cap.
    if os.getenv("VERCEL") or name in {"yahoo", "yahoo_http"}:
        from app.market.yahoo_http import YahooHttpProvider

        return YahooHttpProvider()
    from app.market.yfinance_provider import YFinanceProvider

    return YFinanceProvider()


def _validate(quote: NormalizedQuote) -> NormalizedQuote | None:
    if quote.price <= 0 or quote.previous_close <= 0:
        return None
    if quote.data_status not in VALID_STATUSES:
        quote.data_status = "DELAYED"
    if quote.timestamp.tzinfo is None:
        quote.timestamp = quote.timestamp.replace(tzinfo=UTC)
    age = datetime.now(UTC) - quote.timestamp
    if quote.data_status == "LIVE" and age > timedelta(minutes=5):
        quote.data_status = "STALE"
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
        timestamp=quote.timestamp,
        source=quote.source,
        data_status=quote.data_status,
        market_state=quote.market_state,
    )
    db.add(snap)
    db.flush()
    return snap


def latest_db_snapshot(db: Session, symbol: str) -> MarketSnapshot | None:
    return db.scalar(
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol == symbol.upper())
        .order_by(MarketSnapshot.timestamp.desc())
        .limit(1)
    )


def snapshot_to_quote(snap: MarketSnapshot, status_override: str | None = None) -> NormalizedQuote:
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
        timestamp=snap.timestamp,
        source=snap.source,
        data_status=status_override or snap.data_status,
        market_state=snap.market_state,
    )


class MarketDataService:
    def __init__(self) -> None:
        self.provider = _provider()

    def get_quote(self, db: Session, symbol: str) -> tuple[NormalizedQuote | None, MarketSnapshot | None]:
        symbol = symbol.upper().strip()
        cache_key = f"quote:{settings.market_data_provider}:{symbol}"
        cached = cache_get(cache_key)
        if cached:
            ts = cached.get("timestamp")
            if isinstance(ts, str):
                cached["timestamp"] = datetime.fromisoformat(ts)
            quote = NormalizedQuote(**cached)
            snap = latest_db_snapshot(db, symbol)
            return quote, snap

        quote = None
        try:
            quote = self.provider.get_quote(symbol)
        except Exception:  # noqa: BLE001
            quote = None

        if quote:
            quote = _validate(quote)

        if quote and quote.data_status != "UNAVAILABLE":
            snap = persist_snapshot(db, quote)
            payload = {**quote.__dict__, "timestamp": quote.timestamp.isoformat()}
            cache_set(cache_key, payload, ttl=settings.cache_ttl_seconds)
            return quote, snap

        existing = latest_db_snapshot(db, symbol)
        if existing:
            stale = snapshot_to_quote(existing, "STALE" if quote is None else quote.data_status)
            return stale, existing
        if quote and quote.data_status == "UNAVAILABLE":
            return quote, None
        return None, None

    def _commit_quote(self, db: Session, symbol: str, quote: NormalizedQuote | None):
        if quote:
            quote = _validate(quote)
        if quote and quote.data_status != "UNAVAILABLE":
            persist_snapshot(db, quote)
            payload = {**quote.__dict__, "timestamp": quote.timestamp.isoformat()}
            cache_set(f"quote:{settings.market_data_provider}:{symbol}", payload, ttl=settings.cache_ttl_seconds)

    def prefetch(self, db: Session, symbols: list[str]) -> None:
        needed: list[str] = []
        seen: set[str] = set()
        for raw in symbols:
            symbol = raw.upper().strip()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            if not cache_get(f"quote:{settings.market_data_provider}:{symbol}"):
                needed.append(symbol)
        if not needed:
            return
        try:
            fetched = self.provider.get_quotes(needed)
        except Exception:  # noqa: BLE001
            fetched = {s: None for s in needed}
        for symbol in needed:
            self._commit_quote(db, symbol, fetched.get(symbol))

    def search(self, db: Session, query: str) -> list[NormalizedQuote]:
        try:
            results = self.provider.search(query)
        except Exception:  # noqa: BLE001
            results = []
        cleaned = []
        for item in results:
            valid = _validate(item)
            if valid:
                cleaned.append(valid)
        return cleaned

    def refresh_symbols(self, db: Session, symbols: list[str]) -> None:
        self.prefetch(db, list(symbols))
        db.commit()


market_service = MarketDataService()
