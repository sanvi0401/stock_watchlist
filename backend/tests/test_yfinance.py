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
    with patch("app.market.yfinance_provider.yf.Ticker", return_value=ticker):
        quote = YFinanceProvider().get_quote("NVDA")
    assert quote is not None
    assert quote.source == "yfinance"
    assert quote.data_status == "DELAYED"
    assert quote.price == 110.0
    assert quote.previous_close == 106.0
    assert quote.company_name == "NVIDIA Corporation"
    ticker.history.assert_called_once()


def test_yfinance_batch_quotes():
    hist = _hist()
    with patch("app.market.yfinance_provider.yf.download", return_value=hist):
        quotes = YFinanceProvider().get_quotes(["NVDA"])
    assert quotes["NVDA"] is not None
    assert quotes["NVDA"].price == 110.0
    assert quotes["NVDA"].source == "yfinance"


def test_yfinance_search_uses_yahoo_fields_without_history():
    row = {
        "symbol": "MSFT",
        "shortname": "Microsoft Corporation",
        "quoteType": "EQUITY",
        "regularMarketPrice": 420.5,
        "regularMarketPreviousClose": 418.0,
        "regularMarketVolume": 12_000_000,
    }
    with patch("app.market.yfinance_provider.yf.Search") as search:
        search.return_value.quotes = [row]
        results = YFinanceProvider().search("microsoft")
    assert results[0].symbol == "MSFT"
    assert results[0].price == 420.5
    assert results[0].source == "yfinance"


def test_yfinance_returns_none_on_failure():
    with patch("app.market.yfinance_provider.yf.Ticker", side_effect=RuntimeError("boom")):
        quote = YFinanceProvider().get_quote("COST")
    assert quote is None
