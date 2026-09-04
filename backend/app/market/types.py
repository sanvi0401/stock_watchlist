from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


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
    # Exchange context. Every provider fills these; the service never assumes US/USD.
    currency: str = "USD"
    exchange: str = ""  # Yahoo exchange code, e.g. NSI, NMS, LSE
    exchange_name: str = ""  # human label, e.g. NSE, NasdaqGS
    timezone: str = ""  # IANA zone of the exchange
    session_start: datetime | None = None  # today's regular session, if the provider knows it
    session_end: datetime | None = None


class MarketDataProvider(Protocol):
    def get_quote(self, symbol: str) -> NormalizedQuote | None: ...

    def search(self, query: str) -> list[NormalizedQuote]: ...

    def get_quotes(self, symbols: list[str]) -> dict[str, NormalizedQuote | None]: ...
