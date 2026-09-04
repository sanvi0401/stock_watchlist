from __future__ import annotations

import logging
from datetime import UTC, datetime

import yfinance as yf

from app.market.mock import MockMarketDataProvider, UNIVERSE
from app.market.types import NormalizedQuote

logger = logging.getLogger(__name__)


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


class YFinanceProvider:
    source = "yfinance"

    def _from_history(self, symbol: str) -> NormalizedQuote | None:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y", auto_adjust=True)
        if hist is None or hist.empty:
            return None

        last = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else last
        price = _num(last.get("Close"))
        previous_close = _num(prev.get("Close"))
        if price <= 0 or previous_close <= 0:
            return None

        volume = _num(last.get("Volume"))
        avg_vol = _num(hist["Volume"].tail(60).mean(), volume or 1.0)
        rets = hist["Close"].pct_change().dropna()
        volatility = _num(rets.tail(60).std(), 0.02) or 0.02
        spark = [float(x) for x in hist["Close"].tail(12).tolist() if x == x]

        name = symbol
        market_cap = 0.0
        week_high = _num(hist["High"].max(), price)
        week_low = _num(hist["Low"].min(), price)
        ts = datetime.now(UTC)
        try:
            idx = last.name
            if getattr(idx, "to_pydatetime", None):
                ts = idx.to_pydatetime()
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
                else:
                    ts = ts.astimezone(UTC)
        except Exception:  # noqa: BLE001
            ts = datetime.now(UTC)

        try:
            info = ticker.fast_info
            last_price = _num(getattr(info, "last_price", None))
            prev_close = _num(getattr(info, "previous_close", None))
            if last_price > 0:
                price = last_price
            if prev_close > 0:
                previous_close = prev_close
            market_cap = _num(getattr(info, "market_cap", None))
            yh = _num(getattr(info, "year_high", None))
            yl = _num(getattr(info, "year_low", None))
            if yh > 0:
                week_high = yh
            if yl > 0:
                week_low = yl
            vol = _num(getattr(info, "last_volume", None))
            if vol > 0:
                volume = vol
        except Exception:  # noqa: BLE001
            logger.debug("yfinance fast_info unavailable for %s", symbol, exc_info=True)

        if symbol in UNIVERSE:
            name = UNIVERSE[symbol]["name"]

        return NormalizedQuote(
            symbol=symbol,
            company_name=name,
            price=price,
            previous_close=previous_close,
            volume=volume,
            average_volume=avg_vol or volume,
            volatility=volatility,
            market_cap=market_cap,
            week_52_high=week_high,
            week_52_low=week_low,
            timestamp=ts,
            source=self.source,
            data_status="DELAYED",
            market_state="OPEN",
            sparkline=spark,
        )

    def get_quote(self, symbol: str) -> NormalizedQuote | None:
        key = symbol.upper().strip()
        if not key:
            return None
        try:
            quote = self._from_history(key)
            if quote:
                return quote
        except Exception:  # noqa: BLE001
            logger.warning("yfinance quote failed for %s", key, exc_info=True)
        return MockMarketDataProvider().get_quote(key)

    def search(self, query: str) -> list[NormalizedQuote]:
        q = query.strip()
        if not q:
            return []
        out: list[NormalizedQuote] = []
        seen: set[str] = set()

        try:
            found = yf.Search(q, max_results=8).quotes or []
        except Exception:  # noqa: BLE001
            found = []

        for row in found:
            symbol = str(row.get("symbol") or "").upper()
            if not symbol or symbol in seen:
                continue
            if str(row.get("quoteType") or "").upper() not in {"", "EQUITY", "ETF"}:
                continue
            seen.add(symbol)
            quote = self.get_quote(symbol)
            if quote:
                if row.get("shortname"):
                    quote.company_name = str(row["shortname"])
                out.append(quote)
            if len(out) >= 8:
                return out

        mock_hits = MockMarketDataProvider().search(q)
        for quote in mock_hits:
            if quote.symbol not in seen:
                live = self.get_quote(quote.symbol)
                out.append(live or quote)
                seen.add(quote.symbol)
            if len(out) >= 8:
                break
        return out

    def get_quotes(self, symbols: list[str]) -> dict[str, NormalizedQuote | None]:
        return {s.upper(): self.get_quote(s) for s in symbols}
