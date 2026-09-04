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
    ticker = MagicMock()
    ticker.history.return_value = _hist()
    ticker.history_metadata = {"currency": "USD", "exchangeName": "NMS"}
    with patch("app.market.yfinance_provider.yf.Ticker", return_value=ticker):
        quotes = YFinanceProvider().get_quotes(["NVDA", "AAPL"])
    assert quotes["NVDA"] is not None and quotes["AAPL"] is not None
    assert quotes["NVDA"].price == 110.0
    assert quotes["NVDA"].source == "yfinance"
    assert quotes["NVDA"].currency == "USD"


def test_yfinance_uses_exchange_metadata():
    ticker = MagicMock()
    ticker.history.return_value = _hist()
    ticker.history_metadata = {
        "currency": "INR", "exchangeName": "NSI", "fullExchangeName": "NSE", "exchangeTimezoneName": "Asia/Kolkata",
        "longName": "Infosys Limited", "regularMarketPrice": 111.5, "regularMarketTime": datetime(2026, 8, 8, 9, 0, tzinfo=UTC),
        "currentTradingPeriod": {"regular": {"start": datetime(2026, 8, 8, 3, 45, tzinfo=UTC), "end": datetime(2026, 8, 8, 10, 0, tzinfo=UTC)}},
    }
    with patch("app.market.yfinance_provider.yf.Ticker", return_value=ticker):
        quote = YFinanceProvider().get_quote("INFY.NS")
    assert quote.currency == "INR" and quote.exchange == "NSI" and quote.exchange_name == "NSE"
    assert quote.company_name == "Infosys Limited"
    assert quote.price == 111.5 and quote.previous_close == 106.0
    assert quote.timestamp == datetime(2026, 8, 8, 9, 0, tzinfo=UTC)
    assert quote.session_end == datetime(2026, 8, 8, 10, 0, tzinfo=UTC)


def test_yfinance_search_uses_yahoo_symbol_search_then_history():
    ticker = MagicMock()
    ticker.history.return_value = _hist()
    ticker.history_metadata = {"currency": "INR", "exchangeName": "NSI", "longName": "Infosys Limited"}
    rows = [{"symbol": "INFY.NS", "name": "Infosys Limited", "exchange": "NSI", "exchange_name": "NSE"}]
    with patch("app.market.yfinance_provider.search_rows", return_value=rows), patch(
        "app.market.yfinance_provider.yf.Ticker", return_value=ticker
    ):
        results = YFinanceProvider().search("infosys")
    assert results[0].symbol == "INFY.NS"
    assert results[0].currency == "INR"
    assert results[0].price == 110.0
    assert results[0].source == "yfinance"


def test_yfinance_ignores_nan_close_on_todays_bar():
    from datetime import timedelta

    hist = _hist()
    hist.loc[hist.index[-1], "Close"] = float("nan")  # in-progress session
    ticker = MagicMock()
    ticker.history.return_value = hist
    ticker.history_metadata = {"regularMarketPrice": 112.0, "regularMarketTime": hist.index[-1] + timedelta(hours=10)}
    with patch("app.market.yfinance_provider.yf.Ticker", return_value=ticker):
        quote = YFinanceProvider().get_quote("NVDA")
    assert quote.price == 112.0
    assert quote.previous_close == 106.0  # last finished session, not the NaN bar


def test_previous_close_rule():
    from datetime import timedelta

    from app.market.yahoo_meta import previous_close

    day = datetime(2026, 9, 4, 4, 0, tzinfo=UTC)
    bars = [(day - timedelta(days=2), 100.0), (day - timedelta(days=1), 105.0), (day, 110.0)]
    # print during today's session: today's bar is the last one -> previous is yesterday
    assert previous_close(bars, day + timedelta(hours=10), "America/New_York") == 105.0
    # today's bar not there yet -> the newest bar is the previous close
    assert previous_close(bars[:-1], day + timedelta(hours=10), "America/New_York") == 105.0
    assert previous_close([], None, None) is None


def test_yfinance_falls_back_to_mock_on_failure():
    with patch("app.market.yfinance_provider.yf.Ticker", side_effect=RuntimeError("boom")):
        quote = YFinanceProvider().get_quote("COST")
    assert quote is not None
    assert quote.source == "mock-terminal"
    assert quote.symbol == "COST"
