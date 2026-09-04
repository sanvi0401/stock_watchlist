from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from app.market.yfinance_provider import YFinanceProvider


def _hist():
    idx = pd.date_range("2026-08-01", periods=8, tz="UTC")
    return pd.DataFrame(
        {
            "Open": [100, 101, 102, 103, 104, 105, 106, 107],
            "High": [101, 102, 103, 104, 105, 106, 107, 108],
            "Low": [99, 100, 101, 102, 103, 104, 105, 106],
            "Close": [100, 101, 102, 103, 104, 105, 106, 110],
            "Volume": [1_000_000] * 8,
        },
        index=idx,
    )


def test_yfinance_quote_from_history():
    ticker = MagicMock()
    ticker.history.return_value = _hist()
    ticker.fast_info = MagicMock(
        last_price=110.0,
        previous_close=106.0,
        market_cap=1e12,
        year_high=120.0,
        year_low=80.0,
        last_volume=2_000_000,
    )
    with patch("app.market.yfinance_provider.yf.Ticker", return_value=ticker):
        quote = YFinanceProvider().get_quote("NVDA")
    assert quote is not None
    assert quote.source == "yfinance"
    assert quote.data_status == "DELAYED"
    assert quote.price == 110.0
    assert quote.previous_close == 106.0
    assert quote.company_name == "NVIDIA Corporation"


def test_yfinance_falls_back_to_mock_on_failure():
    with patch("app.market.yfinance_provider.yf.Ticker", side_effect=RuntimeError("boom")):
        quote = YFinanceProvider().get_quote("COST")
    assert quote is not None
    assert quote.source == "mock-terminal"
    assert quote.symbol == "COST"
