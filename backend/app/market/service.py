from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.cache import cache_get, cache_set
from app.config import settings
from app.market.calendar import classify_quote_status, us_equity_session
from app.market.circuit import ProviderLimited, is_cooling_down, note_failure, note_success
from app.market.types import HistoryPoint, NormalizedQuote
from app.models import MarketSnapshot

logger = logging.getLogger(__name__)

VALID_STATUSES = {"LIVE", "DELAYED", "STALE", "UNAVAILABLE"}


def _provider():
    name = (settings.market_data_provider or "yfinance").lower()
    if name == "mock":
        from app.market.mock import MockMarketDataProvider

        return MockMarketDataProvider()
    if name == "alpha_vantage" and settings.alpha_vantage_api_key:
        from app.market.alpha_vantage import AlphaVantageProvider

        return AlphaVantageProvider()
    import os

    if os.getenv("VERCEL") or name in {"yahoo", "yahoo_http"}:
        from app.market.yahoo_http import YahooHttpProvider

        return YahooHttpProvider()
    from app.market.yfinance_provider import YFinanceProvider

    return YFinanceProvider()


def apply_status(quote: NormalizedQuote) -> NormalizedQuote:
    quote.market_state = us_equity_session(quote.timestamp) if quote.data_status != "UNAVAILABLE" else "UNKNOWN"
    quote.data_status = classify_quote_status(quote.data_status, quote.timestamp)
    return quote


def _validate(quote: NormalizedQuote) -> NormalizedQuote | None:
    if quote.price <= 0 or quote.previous_close <= 0:
        return None
    if quote.timestamp.tzinfo is None:
        quote.timestamp = quote.timestamp.replace(tzinfo=UTC)
    return apply_status(quote)


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
        sparkline=json.dumps((quote.recent_closes or quote.sparkline)[-60:]),
    )
    db.add(snap)
    db.flush()
    return snap


def latest_snapshots_map(db: Session, symbols: list[str]) -> dict[str, MarketSnapshot]:
    if not symbols:
        return {}
    subq = (
        select(MarketSnapshot.symbol, func.max(MarketSnapshot.id).label("mid"))
        .where(MarketSnapshot.symbol.in_([s.upper() for s in symbols]))
        .group_by(MarketSnapshot.symbol)
        .subquery()
    )
    rows = db.scalars(select(MarketSnapshot).join(subq, MarketSnapshot.id == subq.c.mid)).all()
    return {r.symbol: r for r in rows}


def latest_db_snapshot(db: Session, symbol: str) -> MarketSnapshot | None:
    return latest_snapshots_map(db, [symbol]).get(symbol.upper())


def snapshot_to_quote(snap: MarketSnapshot, status_override: str | None = None) -> NormalizedQuote:
    closes: list[float] = []
    if snap.sparkline:
        try:
            closes = [float(x) for x in json.loads(snap.sparkline)]
        except (TypeError, ValueError, json.JSONDecodeError):
            closes = []
    quote = NormalizedQuote(
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
        sparkline=closes[-12:],
        recent_closes=closes,
    )
    return apply_status(quote)


def prune_snapshots(db: Session) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=max(settings.snapshot_retention_days, 1))
    result = db.execute(delete(MarketSnapshot).where(MarketSnapshot.timestamp < cutoff))
    return int(result.rowcount or 0)


class MarketDataService:
    def __init__(self) -> None:
        self.provider = _provider()

    def _live_fetch_allowed(self) -> bool:
        return not is_cooling_down()

    def get_quote(self, db: Session, symbol: str) -> tuple[NormalizedQuote | None, MarketSnapshot | None]:
        symbol = symbol.upper().strip()
        cache_key = f"quote:{settings.market_data_provider}:{symbol}"
        cached = cache_get(cache_key)
        if cached:
            ts = cached.get("timestamp")
            if isinstance(ts, str):
                cached["timestamp"] = datetime.fromisoformat(ts)
            cached.pop("sparkline", None)
            recent = cached.pop("recent_closes", None) or []
            quote = NormalizedQuote(**{k: v for k, v in cached.items() if k in NormalizedQuote.__dataclass_fields__})
            quote.recent_closes = recent
            quote.sparkline = recent[-12:]
            quote = apply_status(quote)
            snap = latest_db_snapshot(db, symbol)
            return quote, snap

        quote = None
        if self._live_fetch_allowed():
            try:
                quote = self.provider.get_quote(symbol)
                note_success()
            except ProviderLimited as exc:
                note_failure(429, exc.retry_after)
                quote = None
            except Exception as exc:  # noqa: BLE001
                logger.warning("provider get_quote failed for %s: %s", symbol, exc)
                status = getattr(getattr(exc, "response", None), "status_code", None)
                note_failure(status)
                quote = None

        if quote:
            quote = _validate(quote)

        if quote and quote.data_status != "UNAVAILABLE":
            snap = persist_snapshot(db, quote)
            self._cache_quote(symbol, quote)
            return quote, snap

        existing = latest_db_snapshot(db, symbol)
        if existing:
            stale = snapshot_to_quote(existing)
            if stale.data_status not in {"STALE", "DELAYED", "LIVE"}:
                stale.data_status = "STALE"
            else:
                stale.data_status = classify_quote_status("DELAYED", existing.timestamp)
            return stale, existing
        if quote and quote.data_status == "UNAVAILABLE":
            return quote, None
        return None, None

    def _cache_quote(self, symbol: str, quote: NormalizedQuote) -> None:
        payload = {
            **{k: v for k, v in quote.__dict__.items() if k not in {"sparkline", "recent_closes"}},
            "timestamp": quote.timestamp.isoformat(),
            "recent_closes": quote.recent_closes or quote.sparkline,
        }
        cache_set(f"quote:{settings.market_data_provider}:{symbol}", payload, ttl=settings.cache_ttl_seconds)

    def _commit_quote(self, db: Session, symbol: str, quote: NormalizedQuote | None) -> None:
        if quote:
            quote = _validate(quote)
        if quote and quote.data_status != "UNAVAILABLE":
            persist_snapshot(db, quote)
            self._cache_quote(symbol, quote)

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
        if not needed or not self._live_fetch_allowed():
            return
        try:
            fetched = self.provider.get_quotes(needed)
            note_success()
        except ProviderLimited as exc:
            note_failure(429, exc.retry_after)
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("provider batch failed: %s", exc)
            note_failure(getattr(getattr(exc, "response", None), "status_code", None))
            return
        for symbol in needed:
            self._commit_quote(db, symbol, fetched.get(symbol))

    def search(self, db: Session, query: str) -> list[NormalizedQuote]:
        if not self._live_fetch_allowed() and settings.market_data_provider != "mock":
            return []
        try:
            results = self.provider.search(query)
            note_success()
        except Exception:  # noqa: BLE001
            results = []
        cleaned = []
        for item in results:
            valid = _validate(item)
            if valid:
                cleaned.append(valid)
        from app.symbol_names import NAME_TO_SYMBOL

        hint = NAME_TO_SYMBOL.get((query or "").strip().lower())
        if hint:
            quoted, _ = self.get_quote(db, hint)
            if quoted:
                cleaned = [quoted] + [c for c in cleaned if c.symbol != quoted.symbol]
        return cleaned

    def history(self, db: Session, symbol: str, range_key: str) -> list[HistoryPoint]:
        symbol = symbol.upper()
        cache_key = f"hist:{settings.market_data_provider}:{symbol}:{range_key}"
        cached = cache_get(cache_key)
        if cached:
            out = []
            for row in cached:
                ts = datetime.fromisoformat(row["timestamp"])
                out.append(HistoryPoint(timestamp=ts, close=row["close"], volume=row.get("volume") or 0))
            return out
        points: list[HistoryPoint] = []
        if self._live_fetch_allowed():
            try:
                points = self.provider.get_history(symbol, range_key)
            except Exception:  # noqa: BLE001
                logger.warning("history fetch failed for %s", symbol, exc_info=True)
                points = []
        if not points:
            return []
        payload = [
            {"timestamp": p.timestamp.isoformat(), "close": p.close, "volume": p.volume} for p in points
        ]
        cache_set(cache_key, payload, ttl=max(settings.cache_ttl_seconds, 120))
        return points

    def refresh_symbols(self, db: Session, symbols: list[str]) -> None:
        self.prefetch(db, list(symbols))
        prune_snapshots(db)
        db.commit()


market_service = MarketDataService()
