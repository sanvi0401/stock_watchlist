from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

import httpx

from app.market.calendar import us_equity_session
from app.market.circuit import ProviderLimited
from app.market.types import HistoryPoint, NormalizedQuote

logger = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_SEARCH = "https://query1.finance.yahoo.com/v1/finance/search"


def _num(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        n = float(value)
        if n != n:
            return default
        return n
    except (TypeError, ValueError):
        return default


class YahooHttpProvider:
    """Delayed Yahoo quotes over public chart/search HTTP APIs (no pandas/yfinance)."""

    source = "yfinance"

    def __init__(self) -> None:
        self._client = httpx.Client(timeout=12.0, headers={"User-Agent": _UA, "Accept": "application/json"})

    def _from_chart(self, symbol: str) -> NormalizedQuote | None:
        resp = self._client.get(
            _CHART.format(symbol=symbol),
            params={"interval": "1d", "range": "1y"},
        )
        resp.raise_for_status()
        payload = resp.json()
        results = (payload.get("chart") or {}).get("result") or []
        if not results:
            return None
        result = results[0]
        meta = result.get("meta") or {}
        quotes = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        closes = [c for c in (quotes.get("close") or []) if c is not None]
        highs = [c for c in (quotes.get("high") or []) if c is not None]
        lows = [c for c in (quotes.get("low") or []) if c is not None]
        volumes = [c for c in (quotes.get("volume") or []) if c is not None]
        if len(closes) < 2:
            return None

        price = _num(meta.get("regularMarketPrice"), closes[-1])
        previous_close = closes[-2]
        if price <= 0 or previous_close <= 0:
            return None

        volume = _num(meta.get("regularMarketVolume"), volumes[-1] if volumes else 0)
        avg_vol = sum(volumes[-60:]) / max(len(volumes[-60:]), 1) if volumes else volume
        rets = []
        window = closes[-61:]
        for i in range(1, len(window)):
            if window[i - 1]:
                rets.append((window[i] - window[i - 1]) / window[i - 1])
        if rets:
            mean = sum(rets) / len(rets)
            variance = sum((x - mean) ** 2 for x in rets) / len(rets)
            volatility = variance ** 0.5 or 0.02
        else:
            volatility = 0.02

        spark = [float(x) for x in closes[-12:]]
        name = str(meta.get("shortName") or symbol)
        ts = datetime.now(UTC)
        try:
            stamps = result.get("timestamp") or []
            if stamps:
                ts = datetime.fromtimestamp(int(stamps[-1]), tz=UTC)
        except (TypeError, ValueError, OSError):
            ts = datetime.now(UTC)

        return NormalizedQuote(
            symbol=symbol,
            company_name=name,
            price=price,
            previous_close=_num(previous_close),
            volume=volume,
            average_volume=_num(avg_vol, volume),
            volatility=volatility,
            market_cap=0.0,
            week_52_high=_num(meta.get("fiftyTwoWeekHigh"), max(highs) if highs else price),
            week_52_low=_num(meta.get("fiftyTwoWeekLow"), min(lows) if lows else price),
            timestamp=ts,
            source=self.source,
            data_status="DELAYED",
            market_state=us_equity_session(ts),
            sparkline=spark,
            recent_closes=[float(x) for x in closes[-60:]],
        )

    def get_quote(self, symbol: str) -> NormalizedQuote | None:
        key = symbol.upper().strip()
        if not key:
            return None
        try:
            quote = self._from_chart(key)
            if quote:
                return quote
        except httpx.HTTPStatusError as exc:
            if exc.response is not None and exc.response.status_code == 429:
                raise ProviderLimited(60) from exc
            logger.warning("yahoo http quote failed for %s", key, exc_info=True)
        except Exception:  # noqa: BLE001
            logger.warning("yahoo http quote failed for %s", key, exc_info=True)
        return None

    def search(self, query: str) -> list[NormalizedQuote]:
        q = query.strip()
        if not q:
            return []
        symbols: list[str] = []
        names: dict[str, str] = {}
        try:
            resp = self._client.get(_SEARCH, params={"q": q, "quotesCount": 8, "newsCount": 0})
            resp.raise_for_status()
            rows = resp.json().get("quotes") or []
        except Exception:  # noqa: BLE001
            rows = []
        for row in rows:
            symbol = str(row.get("symbol") or "").upper()
            qtype = str(row.get("quoteType") or "").upper()
            if not symbol or symbol in names:
                continue
            if qtype not in {"", "EQUITY", "ETF"}:
                continue
            names[symbol] = str(row.get("shortname") or row.get("longname") or symbol)
            symbols.append(symbol)
            if len(symbols) >= 6:
                break
        quotes = self.get_quotes(symbols)
        out: list[NormalizedQuote] = []
        for symbol in symbols:
            quote = quotes.get(symbol)
            if quote:
                if names.get(symbol):
                    quote.company_name = names[symbol]
                out.append(quote)
        if len(out) < 8:
            return out
        return out

    def get_quotes(self, symbols: list[str]) -> dict[str, NormalizedQuote | None]:
        keys: list[str] = []
        for raw in symbols:
            key = raw.upper().strip()
            if key and key not in keys:
                keys.append(key)
        if not keys:
            return {}
        out: dict[str, NormalizedQuote | None] = {k: None for k in keys}
        workers = min(8, len(keys))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(self.get_quote, key): key for key in keys}
            for fut in as_completed(futs):
                key = futs[fut]
                try:
                    out[key] = fut.result()
                except ProviderLimited:
                    raise
                except Exception:  # noqa: BLE001
                    out[key] = None
        return out

    def get_history(self, symbol: str, range_key: str) -> list[HistoryPoint]:
        key = symbol.upper().strip()
        params = {
            "1d": {"interval": "5m", "range": "1d"},
            "5d": {"interval": "1d", "range": "5d"},
            "1mo": {"interval": "1d", "range": "1mo"},
            "1y": {"interval": "1d", "range": "1y"},
        }.get(range_key, {"interval": "1d", "range": "5d"})
        try:
            resp = self._client.get(_CHART.format(symbol=key), params=params)
            if resp.status_code == 429:
                raise ProviderLimited(60)
            resp.raise_for_status()
            payload = resp.json()
        except ProviderLimited:
            raise
        except Exception:  # noqa: BLE001
            return []
        results = (payload.get("chart") or {}).get("result") or []
        if not results:
            return []
        result = results[0]
        quotes = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        closes = quotes.get("close") or []
        volumes = quotes.get("volume") or []
        stamps = result.get("timestamp") or []
        points: list[HistoryPoint] = []
        for i, close in enumerate(closes):
            if close is None:
                continue
            ts = datetime.now(UTC)
            if i < len(stamps):
                try:
                    ts = datetime.fromtimestamp(int(stamps[i]), tz=UTC)
                except (TypeError, ValueError, OSError):
                    pass
            vol = _num(volumes[i] if i < len(volumes) else 0)
            points.append(HistoryPoint(timestamp=ts, close=float(close), volume=vol))
        return points
