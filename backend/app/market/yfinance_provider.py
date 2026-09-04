from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

import pandas as pd
import yfinance as yf

from app.market.freshness import session_timestamp
from app.market.mock import UNIVERSE, MockMarketDataProvider
from app.market.types import NormalizedQuote
from app.market.yahoo_meta import exchange_context, get, previous_close, search_rows

logger = logging.getLogger(__name__)

# One year of daily bars is enough for 52-week range + 60-day vol, without extra fast_info round trips.
_HISTORY_PERIOD = "1y"


def _num(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        n = float(value)
        if n != n:  # NaN
            return default
        return n
    except (TypeError, ValueError):
        return default


_META_KEYS = (
    "currency", "exchangeName", "fullExchangeName", "exchangeTimezoneName", "longName", "shortName",
    "regularMarketPrice", "regularMarketVolume", "regularMarketTime", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
    "currentTradingPeriod",
)


def _plain_meta(raw: Any) -> dict:
    """Copy only the keys we use out of yfinance's lazy HistoryMetadata (a dict-like, not a dict),
    keeping only plain values so a mock or a lazy placeholder can never leak into a quote."""
    if raw is None or not hasattr(raw, "get"):
        return {}
    out: dict = {}
    for key in _META_KEYS:
        try:
            value = raw.get(key)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(value, (str, int, float, dict, datetime, pd.Timestamp)):
            out[key] = value
    return out


def _is_throttle(exc: BaseException) -> bool:
    text = str(exc)
    return "429" in text or "Too Many Requests" in text or "Rate limited" in text


class YFinanceProvider:
    """Delayed Yahoo quotes via yfinance, any exchange Yahoo covers (NSE, BSE, NYSE, LSE, ...)."""

    source = "yfinance"

    def _quote_from_hist(self, symbol: str, hist: pd.DataFrame | None, meta: Any = None) -> NormalizedQuote | None:
        if hist is None or getattr(hist, "empty", True) or "Close" not in hist:
            return None
        meta = _plain_meta(meta)
        # Today's in-progress bar can carry a NaN close; never let it become the price.
        valid = hist.dropna(subset=["Close"])
        if valid.empty:
            return None
        ctx = exchange_context(meta)
        bars = [
            (idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx, float(c))
            for idx, c in zip(valid.index, valid["Close"])
        ]
        price = _num(get(meta, "regularMarketPrice"), bars[-1][1])
        prev = previous_close(bars, ctx["print_time"], ctx["timezone"]) or price
        if price <= 0 or prev <= 0:
            return None

        last = valid.iloc[-1]
        volume = _num(get(meta, "regularMarketVolume"), _num(last.get("Volume")))
        avg_vol = _num(valid["Volume"].tail(60).mean(), volume or 1.0) if "Volume" in valid else volume
        rets = valid["Close"].pct_change().dropna()
        volatility = _num(rets.tail(60).std(), 0.02) or 0.02

        ts = ctx["print_time"]
        if ts is None:
            ts = session_timestamp(bars[-1][0], exchange=ctx["exchange"], symbol=symbol, timezone=ctx["timezone"])

        return NormalizedQuote(
            symbol=symbol,
            company_name=ctx["company_name"] or UNIVERSE.get(symbol, {}).get("name") or symbol,
            price=price,
            previous_close=prev,
            volume=volume,
            average_volume=avg_vol or volume,
            volatility=volatility,
            market_cap=0.0,
            week_52_high=_num(get(meta, "fiftyTwoWeekHigh"), _num(valid["High"].max(), price) if "High" in valid else price),
            week_52_low=_num(get(meta, "fiftyTwoWeekLow"), _num(valid["Low"].min(), price) if "Low" in valid else price),
            timestamp=ts,
            source=self.source,
            data_status="DELAYED",
            market_state="UNKNOWN",
            sparkline=[c for _, c in bars[-12:]],
            currency=ctx["currency"],
            exchange=ctx["exchange"],
            exchange_name=ctx["exchange_name"],
            timezone=ctx["timezone"],
            session_start=ctx["session_start"],
            session_end=ctx["session_end"],
        )

    def _from_history(self, symbol: str) -> NormalizedQuote | None:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=_HISTORY_PERIOD, auto_adjust=True)
        return self._quote_from_hist(symbol, hist, getattr(ticker, "history_metadata", None))

    def get_quote(self, symbol: str) -> NormalizedQuote | None:
        key = symbol.upper().strip()
        if not key:
            return None
        try:
            quote = self._from_history(key)
            if quote:
                return quote
        except Exception as exc:  # noqa: BLE001
            if _is_throttle(exc):
                raise  # let the service start a cooldown instead of hammering Yahoo
            logger.warning("yfinance quote failed for %s", key, exc_info=True)
        return MockMarketDataProvider().get_quote(key)

    def search(self, query: str) -> list[NormalizedQuote]:
        """Yahoo's search endpoint finds the symbols (any exchange); quotes come from history so
        every result carries currency, exchange and session data."""
        rows = search_rows(query, limit=8)
        quotes = self.get_quotes([r["symbol"] for r in rows])
        out: list[NormalizedQuote] = []
        for row in rows:
            quote = quotes.get(row["symbol"])
            if quote:
                if quote.source != self.source and row.get("name"):
                    quote.company_name = row["name"]
                out.append(quote)
        seen = {q.symbol for q in out}
        for quote in MockMarketDataProvider().search(query):
            if quote.symbol not in seen and len(out) < 8:
                out.append(quote)
        return out

    def get_quotes(self, symbols: list[str]) -> dict[str, NormalizedQuote | None]:
        unique: list[str] = []
        for raw in symbols:
            key = raw.upper().strip()
            if key and key not in unique:
                unique.append(key)
        if not unique:
            return {}

        # Per-ticker fetches keep the exchange metadata (currency, session); yf.download drops it.
        def one(key: str) -> tuple[str, NormalizedQuote | None, BaseException | None]:
            try:
                return key, self.get_quote(key), None
            except Exception as exc:  # noqa: BLE001
                return key, None, exc

        out: dict[str, NormalizedQuote | None] = {}
        throttled: BaseException | None = None
        with ThreadPoolExecutor(max_workers=min(6, len(unique))) as pool:
            for key, quote, exc in pool.map(one, unique):
                out[key] = quote
                if exc is not None:
                    throttled = exc
        if throttled is not None and not any(out.values()):
            raise throttled  # nothing came back at all: let the service start a cooldown
        return out
