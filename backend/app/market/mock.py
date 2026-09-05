from datetime import UTC, datetime, timedelta

from app.market.types import NormalizedQuote

UNIVERSE: dict[str, dict] = {
    "NVDA": {
        "name": "NVIDIA Corporation",
        "price": 172.38,
        "previous_close": 169.99,
        "volume": 89_400_000,
        "average_volume": 42_100_000,
        "volatility": 0.028,
        "market_cap": 4.23e12,
        "week_52_high": 191.05,
        "week_52_low": 86.62,
        "last_seen_demo": 163.00,
        "spark": [158, 160, 159, 163, 165, 168, 170, 172.38],
    },
    "TSLA": {
        "name": "Tesla, Inc.",
        "price": 218.45,
        "previous_close": 229.40,
        "volume": 142_000_000,
        "average_volume": 98_000_000,
        "volatility": 0.035,
        "market_cap": 7.0e11,
        "week_52_high": 299.29,
        "week_52_low": 138.80,
        "last_seen_demo": 230.20,
        "spark": [238, 232, 228, 226, 224, 220, 219, 218.45],
    },
    "AAPL": {
        "name": "Apple Inc.",
        "price": 232.10,
        "previous_close": 225.12,
        "volume": 68_200_000,
        "average_volume": 54_000_000,
        "volatility": 0.016,
        "market_cap": 3.5e12,
        "week_52_high": 260.10,
        "week_52_low": 164.08,
        "last_seen_demo": 225.10,
        "spark": [220, 222, 224, 226, 228, 230, 231, 232.10],
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "price": 501.20,
        "previous_close": 513.50,
        "volume": 32_100_000,
        "average_volume": 22_400_000,
        "volatility": 0.014,
        "market_cap": 3.72e12,
        "week_52_high": 555.45,
        "week_52_low": 344.79,
        "last_seen_demo": 513.40,
        "spark": [520, 516, 512, 510, 508, 505, 503, 501.20],
    },
    "GOOGL": {
        "name": "Alphabet Inc.",
        "price": 284.10,
        "previous_close": 283.25,
        "volume": 18_400_000,
        "average_volume": 21_000_000,
        "volatility": 0.018,
        "market_cap": 2.2e12,
        "week_52_high": 207.05 if False else 312.0,
        "week_52_low": 140.53,
        "last_seen_demo": 283.20,
        "spark": [280, 281, 282, 283, 283.5, 284, 284.05, 284.10],
    },
    "AMZN": {
        "name": "Amazon.com, Inc.",
        "price": 231.40,
        "previous_close": 231.63,
        "volume": 28_900_000,
        "average_volume": 36_200_000,
        "volatility": 0.019,
        "market_cap": 2.4e12,
        "week_52_high": 242.52,
        "week_52_low": 151.61,
        "last_seen_demo": 231.60,
        "spark": [230, 230.5, 231, 231.2, 231.4, 231.5, 231.45, 231.40],
    },
    "META": {
        "name": "Meta Platforms, Inc.",
        "price": 582.60,
        "previous_close": 580.28,
        "volume": 12_400_000,
        "average_volume": 14_100_000,
        "volatility": 0.021,
        "market_cap": 1.48e12,
        "week_52_high": 638.39,
        "week_52_low": 414.50,
        "last_seen_demo": 580.20,
        "spark": [575, 577, 578, 580, 581, 582, 582.4, 582.60],
    },
    "AMD": {
        "name": "Advanced Micro Devices",
        "price": 156.22,
        "previous_close": 155.80,
        "volume": 41_000_000,
        "average_volume": 44_200_000,
        "volatility": 0.031,
        "market_cap": 2.52e11,
        "week_52_high": 227.30,
        "week_52_low": 76.48,
        "last_seen_demo": 155.70,
        "spark": [154, 154.5, 155, 155.4, 155.8, 156, 156.1, 156.22],
    },
    "CRM": {
        "name": "Salesforce, Inc.",
        "price": 273.15,
        "previous_close": 272.40,
        "volume": 6_100_000,
        "average_volume": 6_800_000,
        "volatility": 0.022,
        "market_cap": 2.62e11,
        "week_52_high": 369.00,
        "week_52_low": 226.48,
        "last_seen_demo": 272.50,
        "spark": [271, 271.5, 272, 272.4, 272.8, 273, 273.1, 273.15],
    },
    "COST": {
        "name": "Costco Wholesale",
        "price": 918.40,
        "previous_close": 916.10,
        "volume": 1_800_000,
        "average_volume": 2_100_000,
        "volatility": 0.012,
        "market_cap": 4.07e11,
        "week_52_high": 996.25,
        "week_52_low": 704.26,
        "last_seen_demo": 916.00,
        "spark": [914, 915, 916, 916.5, 917, 917.8, 918.1, 918.40],
    },
    "PLTR": {
        "name": "Palantir Technologies",
        "price": 41.88,
        "previous_close": 39.20,
        "volume": 92_000_000,
        "average_volume": 48_000_000,
        "volatility": 0.042,
        "market_cap": 9.4e10,
        "week_52_high": 45.00,
        "week_52_low": 15.66,
        "last_seen_demo": 39.10,
        "spark": [38, 38.5, 39, 39.8, 40.4, 41, 41.5, 41.88],
    },
    "AVGO": {
        "name": "Broadcom Inc.",
        "price": 172.05,
        "previous_close": 168.40,
        "volume": 22_000_000,
        "average_volume": 18_500_000,
        "volatility": 0.024,
        "market_cap": 8.1e11,
        "week_52_high": 184.0,
        "week_52_low": 120.0,
        "last_seen_demo": 168.20,
        "spark": [166, 167, 168, 169, 170, 171, 171.5, 172.05],
    },
}


class MockMarketDataProvider:
    source = "mock-terminal"

    def __init__(self, force_status: str | None = None) -> None:
        self.force_status = force_status

    def _to_quote(self, symbol: str, row: dict) -> NormalizedQuote:
        status = self.force_status or "DELAYED"
        now = datetime.now(UTC)
        if status == "STALE":
            now = now - timedelta(hours=6)
        if status == "DELAYED":
            now = now - timedelta(minutes=15)
        if status == "LIVE":
            now = datetime.now(UTC)
        spark = list(row.get("spark") or [])
        from app.market.calendar import us_equity_session

        return NormalizedQuote(
            symbol=symbol,
            company_name=row["name"],
            price=float(row["price"]),
            previous_close=float(row["previous_close"]),
            volume=float(row["volume"]),
            average_volume=float(row["average_volume"]),
            volatility=float(row["volatility"]),
            market_cap=float(row["market_cap"]),
            week_52_high=float(row["week_52_high"]),
            week_52_low=float(row["week_52_low"]),
            timestamp=now,
            source=self.source,
            data_status=status,
            market_state="UNKNOWN" if status == "UNAVAILABLE" else us_equity_session(now),
            sparkline=spark,
            recent_closes=spark,
        )

    def get_quote(self, symbol: str) -> NormalizedQuote | None:
        key = symbol.upper().strip()
        row = UNIVERSE.get(key)
        if not row:
            return None
        if self.force_status == "UNAVAILABLE":
            q = self._to_quote(key, row)
            q.data_status = "UNAVAILABLE"
            return q
        return self._to_quote(key, row)

    def search(self, query: str) -> list[NormalizedQuote]:
        q = query.lower().strip()
        if not q:
            return []
        out: list[NormalizedQuote] = []
        for symbol, row in UNIVERSE.items():
            if q in symbol.lower() or q in row["name"].lower():
                quote = self.get_quote(symbol)
                if quote:
                    out.append(quote)
        return out[:12]

    def get_history(self, symbol: str, range_key: str) -> list:
        from app.market.types import HistoryPoint

        quote = self.get_quote(symbol)
        if not quote:
            return []
        n = {"1d": 2, "5d": 5, "1mo": 21, "1y": min(len(quote.recent_closes), 60)}.get(range_key, 5)
        closes = quote.recent_closes[-n:] if quote.recent_closes else [quote.price]
        now = quote.timestamp
        out = []
        for i, c in enumerate(closes):
            ts = now - timedelta(days=len(closes) - 1 - i)
            out.append(HistoryPoint(timestamp=ts, close=c, volume=quote.volume))
        return out

    def get_quotes(self, symbols: list[str]) -> dict[str, NormalizedQuote | None]:
        return {s.upper(): self.get_quote(s) for s in symbols}
