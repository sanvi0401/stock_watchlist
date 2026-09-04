from __future__ import annotations

import logging
from datetime import UTC, datetime

import pandas as pd
import yfinance as yf

from app.market.calendar import us_equity_session
from app.market.circuit import ProviderLimited
from app.market.types import HistoryPoint, NormalizedQuote

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


class YFinanceProvider:
    source = "yfinance"

    def _quote_from_hist(self, symbol: str, hist: pd.DataFrame | None) -> NormalizedQuote | None:
        if hist is None or getattr(hist, "empty", True):
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

        from app.market.mock import UNIVERSE

        name = str(UNIVERSE.get(symbol, {}).get("name") or symbol)
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

        closes = [float(x) for x in hist["Close"].tail(60).tolist() if x == x]
        return NormalizedQuote(
            symbol=symbol,
            company_name=name,
            price=price,
            previous_close=previous_close,
            volume=volume,
            average_volume=avg_vol or volume,
            volatility=volatility,
            market_cap=0.0,
            week_52_high=week_high,
            week_52_low=week_low,
            timestamp=ts,
            source=self.source,
            data_status="DELAYED",
            market_state=us_equity_session(ts),
            sparkline=spark,
            recent_closes=closes,
        )

    def _from_history(self, symbol: str) -> NormalizedQuote | None:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=_HISTORY_PERIOD, auto_adjust=True)
        return self._quote_from_hist(symbol, hist)

    @staticmethod
    def _slice_download(data: pd.DataFrame, symbol: str, count: int) -> pd.DataFrame | None:
        if data is None or getattr(data, "empty", True):
            return None
        if count == 1:
            return data
        if isinstance(data.columns, pd.MultiIndex):
            level0 = data.columns.get_level_values(0)
            if symbol in level0:
                return data[symbol]
            if symbol in data.columns.get_level_values(-1):
                return data.xs(symbol, axis=1, level=-1)
        return None

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
        return None

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
            quote = self._from_search_row(row)
            if quote:
                out.append(quote)
            if len(out) >= 8:
                return out
        return out

    def _from_search_row(self, row: dict) -> NormalizedQuote | None:
        symbol = str(row.get("symbol") or "").upper()
        price = _num(row.get("regularMarketPrice"))
        previous_close = _num(row.get("regularMarketPreviousClose"))
        if price <= 0:
            return None
        if previous_close <= 0:
            previous_close = price
        name = str(row.get("shortname") or row.get("longname") or symbol)
        volume = _num(row.get("regularMarketVolume"))
        return NormalizedQuote(
            symbol=symbol,
            company_name=name,
            price=price,
            previous_close=previous_close,
            volume=volume,
            average_volume=volume or 1.0,
            volatility=0.02,
            market_cap=_num(row.get("marketCap")),
            week_52_high=_num(row.get("fiftyTwoWeekHigh"), price),
            week_52_low=_num(row.get("fiftyTwoWeekLow"), price),
            timestamp=datetime.now(UTC),
            source=self.source,
            data_status="DELAYED",
            market_state=us_equity_session(),
            sparkline=[],
        )

    def get_quotes(self, symbols: list[str]) -> dict[str, NormalizedQuote | None]:
        keys = [s.upper().strip() for s in symbols if s and s.strip()]
        unique: list[str] = []
        for key in keys:
            if key not in unique:
                unique.append(key)
        if not unique:
            return {}

        out: dict[str, NormalizedQuote | None] = {k: None for k in unique}
        try:
            data = yf.download(
                tickers=unique,
                period=_HISTORY_PERIOD,
                group_by="ticker",
                auto_adjust=True,
                threads=True,
                progress=False,
            )
        except Exception:  # noqa: BLE001
            logger.warning("yfinance batch download failed", exc_info=True)
            return {k: self.get_quote(k) for k in unique}

        for key in unique:
            hist = self._slice_download(data, key, len(unique))
            out[key] = self._quote_from_hist(key, hist)
        return out

    def get_history(self, symbol: str, range_key: str) -> list[HistoryPoint]:
        period, interval = {
            "1d": ("1d", "5m"),
            "5d": ("5d", "1d"),
            "1mo": ("1mo", "1d"),
            "1y": ("1y", "1d"),
        }.get(range_key, ("5d", "1d"))
        try:
            hist = yf.Ticker(symbol.upper()).history(period=period, interval=interval, auto_adjust=True)
        except Exception:  # noqa: BLE001
            return []
        if hist is None or getattr(hist, "empty", True):
            return []
        points: list[HistoryPoint] = []
        for idx, row in hist.iterrows():
            close = _num(row.get("Close"))
            if close <= 0:
                continue
            ts = datetime.now(UTC)
            try:
                ts = idx.to_pydatetime()
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
                else:
                    ts = ts.astimezone(UTC)
            except Exception:  # noqa: BLE001
                pass
            points.append(HistoryPoint(timestamp=ts, close=close, volume=_num(row.get("Volume"))))
        return points
