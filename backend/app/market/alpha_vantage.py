from datetime import UTC, datetime

import httpx

from app.config import settings
from app.market.types import NormalizedQuote


class AlphaVantageProvider:
    source = "alpha_vantage"

    def get_quote(self, symbol: str) -> NormalizedQuote | None:
        if not settings.alpha_vantage_api_key:
            return None
        try:
            resp = httpx.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol.upper(),
                    "apikey": settings.alpha_vantage_api_key,
                },
                timeout=8.0,
            )
            resp.raise_for_status()
            data = resp.json().get("Global Quote") or {}
            price = float(data.get("05. price") or 0)
            prev = float(data.get("08. previous close") or 0)
            volume = float(data.get("06. volume") or 0)
            if price <= 0 or prev <= 0:
                return None
            return NormalizedQuote(
                symbol=symbol.upper(),
                company_name=symbol.upper(),
                price=price,
                previous_close=prev,
                volume=volume,
                average_volume=volume,
                volatility=0.02,
                market_cap=0,
                week_52_high=price,
                week_52_low=price,
                timestamp=datetime.now(UTC),
                source=self.source,
                data_status="DELAYED",
                market_state="UNKNOWN",
                exchange="",
            )
        except Exception:  # noqa: BLE001
            return None

    def search(self, query: str) -> list[NormalizedQuote]:
        quote = self.get_quote(query)
        return [quote] if quote else []

    def get_quotes(self, symbols: list[str]) -> dict[str, NormalizedQuote | None]:
        return {s.upper(): self.get_quote(s) for s in symbols}
