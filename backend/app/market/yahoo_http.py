from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

import httpx

from app.market.freshness import session_timestamp
from app.market.mock import UNIVERSE, MockMarketDataProvider
from app.market.types import NormalizedQuote
from app.market.yahoo_meta import exchange_context, previous_close, search_rows

logger = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


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
    """Delayed Yahoo quotes over public chart/search HTTP APIs (no pandas/yfinance). Any exchange."""

    source = "yahoo"

    def __init__(self) -> None:
        self._client = httpx.Client(timeout=12.0, headers={"User-Agent": _UA, "Accept": "application/json"})

    def _from_chart(self, symbol: str) -> NormalizedQuote | None:
        resp = self._client.get(_CHART.format(symbol=symbol), params={"interval": "1d", "range": "1y"})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        payload = resp.json()
        results = (payload.get("chart") or {}).get("result") or []
        if not results:
            return None
        result = results[0]
        meta = result.get("meta") or {}
        quotes = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        stamps = result.get("timestamp") or []
        bars: list[tuple[datetime, float]] = []
        for i, c in enumerate(quotes.get("close") or []):
            if c is None or c != c:
                continue
            try:
                when = datetime.fromtimestamp(int(stamps[i]), tz=UTC) if i < len(stamps) else datetime.now(UTC)
            except (TypeError, ValueError, OSError):
                when = datetime.now(UTC)
            bars.append((when, float(c)))
        closes = [c for _, c in bars]
        highs = [c for c in (quotes.get("high") or []) if c is not None]
        lows = [c for c in (quotes.get("low") or []) if c is not None]
        volumes = [c for c in (quotes.get("volume") or []) if c is not None]
        if not closes:
            return None

        ctx = exchange_context(meta)
        price = _num(meta.get("regularMarketPrice"), closes[-1])
        prev = previous_close(bars, ctx["print_time"], ctx["timezone"]) or price
        if price <= 0 or prev <= 0:
            return None

        volume = _num(meta.get("regularMarketVolume"), volumes[-1] if volumes else 0)
        window_v = volumes[-60:]
        avg_vol = sum(window_v) / len(window_v) if window_v else volume
        rets = []
        window = closes[-61:]
        for i in range(1, len(window)):
            if window[i - 1]:
                rets.append((window[i] - window[i - 1]) / window[i - 1])
        if rets:
            mean = sum(rets) / len(rets)
            volatility = (sum((x - mean) ** 2 for x in rets) / len(rets)) ** 0.5 or 0.02
        else:
            volatility = 0.02

        ts = ctx["print_time"]
        if ts is None:
            ts = session_timestamp(bars[-1][0], exchange=ctx["exchange"], symbol=symbol, timezone=ctx["timezone"])

        return NormalizedQuote(
            symbol=symbol,
            company_name=ctx["company_name"] or UNIVERSE.get(symbol, {}).get("name") or symbol,
            price=price,
            previous_close=prev,
            volume=volume,
            average_volume=_num(avg_vol, volume),
            volatility=volatility,
            market_cap=0.0,
            week_52_high=_num(meta.get("fiftyTwoWeekHigh"), max(highs) if highs else price),
            week_52_low=_num(meta.get("fiftyTwoWeekLow"), min(lows) if lows else price),
            timestamp=ts,
            source=self.source,
            data_status="DELAYED",
            market_state="UNKNOWN",
            sparkline=closes[-12:],
            currency=ctx["currency"],
            exchange=ctx["exchange"],
            exchange_name=ctx["exchange_name"],
            timezone=ctx["timezone"],
            session_start=ctx["session_start"],
            session_end=ctx["session_end"],
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
            if exc.response.status_code == 429:
                raise  # let the service start a cooldown instead of hammering Yahoo
            logger.warning("yahoo http quote failed for %s: %s", key, exc)
        except Exception:  # noqa: BLE001
            logger.warning("yahoo http quote failed for %s", key, exc_info=True)
        return MockMarketDataProvider().get_quote(key)

    def search(self, query: str) -> list[NormalizedQuote]:
        rows = search_rows(query, limit=8, client=self._client)
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
        keys: list[str] = []
        for raw in symbols:
            key = raw.upper().strip()
            if key and key not in keys:
                keys.append(key)
        if not keys:
            return {}
        out: dict[str, NormalizedQuote | None] = {k: None for k in keys}
        throttled: BaseException | None = None
        with ThreadPoolExecutor(max_workers=min(8, len(keys))) as pool:
            futs = {pool.submit(self.get_quote, key): key for key in keys}
            for fut in as_completed(futs):
                key = futs[fut]
                try:
                    out[key] = fut.result()
                except Exception as exc:  # noqa: BLE001
                    throttled = exc
        if throttled is not None and not any(out.values()):
            raise throttled
        return out
