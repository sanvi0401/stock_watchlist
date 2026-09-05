from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class HistoryPoint:
    timestamp: datetime
    close: float
    volume: float = 0.0


@dataclass
class NormalizedQuote:
    symbol: str
    company_name: str
    price: float
    previous_close: float
    volume: float
    average_volume: float
    volatility: float
    market_cap: float
    week_52_high: float
    week_52_low: float
    timestamp: datetime
    source: str
    data_status: str
    market_state: str
    sparkline: list[float] = field(default_factory=list)
    recent_closes: list[float] = field(default_factory=list)


class MarketDataProvider(Protocol):
    def get_quote(self, symbol: str) -> NormalizedQuote | None: ...

    def search(self, query: str) -> list[NormalizedQuote]: ...

    def get_quotes(self, symbols: list[str]) -> dict[str, NormalizedQuote | None]: ...

    def get_history(self, symbol: str, range_key: str) -> list[HistoryPoint]: ...
