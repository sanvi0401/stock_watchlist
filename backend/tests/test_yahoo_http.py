from unittest.mock import MagicMock, patch

from app.market.yahoo_http import YahooHttpProvider


def _chart_payload():
    closes = [100, 101, 102, 103, 104, 105, 106, 110]
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": 110.0,
                        "regularMarketVolume": 2_000_000,
                        "fiftyTwoWeekHigh": 120.0,
                        "fiftyTwoWeekLow": 80.0,
                        "shortName": "NVIDIA Corporation",
                    },
                    "timestamp": [1, 2, 3, 4, 5, 6, 7, 8],
                    "indicators": {
                        "quote": [
                            {
                                "close": closes,
                                "high": [x + 1 for x in closes],
                                "low": [x - 1 for x in closes],
                                "volume": [1_000_000] * 8,
                            }
                        ]
                    },
                }
            ]
        }
    }


def test_yahoo_http_quote_from_chart():
    provider = YahooHttpProvider()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = _chart_payload()
    with patch.object(provider, "_client") as client:
        client.get.return_value = response
        quote = provider.get_quote("NVDA")
    assert quote is not None
    assert quote.source == "yfinance"
    assert quote.data_status == "DELAYED"
    assert quote.price == 110.0
    assert quote.previous_close == 106.0
    assert quote.company_name == "NVIDIA Corporation"


def test_yahoo_http_falls_back_to_mock():
    provider = YahooHttpProvider()
    with patch.object(provider, "_client") as client:
        client.get.side_effect = RuntimeError("boom")
        quote = provider.get_quote("COST")
    assert quote is not None
    assert quote.source == "mock-terminal"
    assert quote.symbol == "COST"
