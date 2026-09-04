"""Multi-exchange behaviour: NSE hours, currencies, symbol suffixes, search ranking, cooldown."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from app import cache
from app.market.freshness import exchange_for, major_markets, market_state, session_timestamp
from app.market.mock import MockMarketDataProvider
from app.market.service import MarketDataService, _validate, provider_cooldown_remaining
from app.market.types import NormalizedQuote
from app.market.yahoo_http import YahooHttpProvider
from app.symbols import looks_like_symbol
from tests.conftest import TestingSession, auth_headers, client


def test_nse_session_hours_in_ist():
    # Monday 2026-09-07 10:00 IST = 04:30 UTC -> NSE open, NYSE closed
    now = datetime(2026, 9, 7, 4, 30, tzinfo=UTC)
    assert market_state(now, exchange="NSI") == "OPEN"
    assert market_state(now, exchange="NYQ") == "PRE_MARKET"  # 00:30 ET
    assert market_state(datetime(2026, 9, 7, 15, 0, tzinfo=UTC), exchange="NYQ") == "OPEN"
    assert market_state(now, symbol="TCS.NS") == "OPEN"
    # 16:00 IST -> NSE closed
    assert market_state(datetime(2026, 9, 7, 10, 30, tzinfo=UTC), exchange="NSI") == "CLOSED"
    assert market_state(datetime(2026, 9, 7, 3, 0, tzinfo=UTC), exchange="NSI") == "PRE_MARKET"


def test_provider_session_window_beats_table_and_detects_holiday():
    now = datetime(2026, 9, 7, 5, 0, tzinfo=UTC)  # Monday 10:30 IST
    start = datetime(2026, 9, 7, 3, 45, tzinfo=UTC)
    end = datetime(2026, 9, 7, 10, 0, tzinfo=UTC)
    assert market_state(now, exchange="NSI", session_start=start, session_end=end) == "OPEN"
    # Provider says the next regular session is tomorrow: today is a holiday.
    tomorrow = timedelta(days=1)
    assert market_state(now, exchange="NSI", session_start=start + tomorrow, session_end=end + tomorrow) == "CLOSED"


def test_exchange_from_suffix_and_currency():
    assert exchange_for(None, "RELIANCE.NS").currency == "INR"
    assert exchange_for(None, "VOD.L").timezone == "Europe/London"
    assert exchange_for("NYQ").name == "NYSE"
    assert exchange_for(None, "AAPL").currency == "USD"


def test_pence_quotes_are_normalised_to_pounds():
    q = MockMarketDataProvider().get_quote("NVDA")
    q.symbol, q.currency, q.exchange = "VOD.L", "GBp", "LSE"
    q.price, q.previous_close, q.sparkline = 125.6, 124.0, [120.0, 125.6]
    out = _validate(q)
    assert out.currency == "GBP"
    assert out.price == 1.256 and out.previous_close == 1.24
    assert out.sparkline == [1.2, 1.256]


def test_symbol_shapes():
    assert looks_like_symbol("RELIANCE.NS")
    assert looks_like_symbol("BRK-B")
    assert looks_like_symbol("^NSEI")
    assert looks_like_symbol("7203.T")
    assert not looks_like_symbol("HDFC BANK")


def test_daily_bar_timestamp_uses_exchange_close():
    now = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
    friday_bar = datetime(2026, 9, 4, 0, 0, tzinfo=UTC)
    ts = session_timestamp(friday_bar, now, exchange="NSI")
    assert ts == datetime(2026, 9, 4, 10, 0, tzinfo=UTC)  # 15:30 IST


def test_search_prefers_nse_and_drops_bse_twin():
    db = TestingSession()
    service = MarketDataService()
    base = MockMarketDataProvider().get_quote("NVDA")

    def mk(symbol, exchange, name):
        q = NormalizedQuote(**{**base.__dict__, "symbol": symbol, "exchange": exchange, "company_name": name, "currency": ""})
        q.exchange_name = ""
        return q

    class Fake:
        def search(self, q):
            return [
                mk("0221.KL", "KLS", "TCS"),
                mk("TCS.BO", "BSE", "Tata Consultancy Services"),
                mk("TCS.NS", "NSI", "Tata Consultancy Services"),
                mk("TCS.DE", "GER", "Axon"),
            ]

    service.provider = Fake()
    hits = service.search(db, "tata consultancy")
    assert [h.symbol for h in hits][:2] == ["TCS.NS", "0221.KL"] or hits[0].symbol == "TCS.NS"
    assert "TCS.BO" not in [h.symbol for h in hits]
    assert hits[0].currency == "INR"


def test_yahoo_http_parses_exchange_context():
    provider = YahooHttpProvider()
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    closes = [100, 101, 102, 103, 104, 105, 106, 110]
    response.json.return_value = {
        "chart": {"result": [{
            "meta": {
                "regularMarketPrice": 110.0, "regularMarketVolume": 2_000_000, "currency": "INR",
                "exchangeName": "NSI", "fullExchangeName": "NSE", "exchangeTimezoneName": "Asia/Kolkata",
                "longName": "Reliance Industries Limited", "regularMarketTime": 1788515100,
                "currentTradingPeriod": {"regular": {"start": 1788493500, "end": 1788516000}},
            },
            "timestamp": list(range(8)),
            "indicators": {"quote": [{"close": closes, "high": closes, "low": closes, "volume": [1] * 8}]},
        }]}
    }
    with patch.object(provider, "_client") as c:
        c.get.return_value = response
        q = provider.get_quote("RELIANCE.NS")
    assert q.currency == "INR" and q.exchange == "NSI" and q.exchange_name == "NSE"
    assert q.timezone == "Asia/Kolkata"
    assert q.timestamp == datetime.fromtimestamp(1788515100, tz=UTC)
    assert q.session_end == datetime.fromtimestamp(1788516000, tz=UTC)
    assert q.company_name == "Reliance Industries Limited"


def test_snapshot_round_trips_exchange_fields():
    db = TestingSession()
    service = MarketDataService()
    service.provider = MockMarketDataProvider()
    cache.cache_delete("quote:mock:RELIANCE.NS")
    quote, snap = service.get_quote(db, "RELIANCE.NS")
    db.commit()
    assert quote.currency == "INR" and snap.currency == "INR" and snap.exchange == "NSI"
    from app.market.service import snapshot_to_quote

    restored = snapshot_to_quote(snap)
    assert restored.currency == "INR" and restored.timezone == "Asia/Kolkata"


def test_provider_failure_starts_cooldown_and_serves_snapshot():
    db = TestingSession()
    service = MarketDataService()
    service.provider = MockMarketDataProvider()
    quote, _ = service.get_quote(db, "INFY.NS")
    db.commit()
    cache.cache_delete("quote:mock:INFY.NS")
    cache.cache_delete("provider:cooldown_until")

    class Broken:
        def get_quote(self, symbol):
            raise RuntimeError("429 Too Many Requests")

    service.provider = Broken()
    fallback, _ = service.get_quote(db, "INFY.NS")
    assert fallback.data_status == "STALE" and fallback.price == quote.price
    assert provider_cooldown_remaining() > 0
    cache.cache_delete("provider:cooldown_until")


def test_end_to_end_indian_watchlist():
    h = auth_headers()
    created = client.post("/watchlists", json={"name": "India", "symbols": ["reliance", "TCS.NS", "infosys"]}, headers=h)
    assert created.status_code == 201
    symbols = sorted(s["symbol"] for s in created.json()["stocks"])
    assert symbols == ["INFY.NS", "RELIANCE.NS", "TCS.NS"]
    assert all(s["quote"]["currency"] == "INR" for s in created.json()["stocks"])
    dash = client.get("/dashboard", headers=h).json()
    assert dash["markets"][0]["exchange"] == "NSI"
    detail = client.get("/stocks/RELIANCE.NS", headers=h).json()
    assert detail["currency"] == "INR" and detail["exchange_name"] == "NSE"
    hist = client.get("/changes/history", headers=h).json()["items"]
    assert all(i["currency"] == "INR" for i in hist)
    found = client.get("/stocks/search", params={"q": "hdfc bank"}, headers=h).json()
    assert found[0]["symbol"] == "HDFCBANK.NS" and found[0]["currency"] == "INR"


def test_health_lists_home_and_us_markets():
    body = client.get("/health").json()
    assert [m["exchange"] for m in body["markets"]] == ["NSI", "NYQ"]
    assert body["provider_cooldown_seconds"] == 0
    assert len(major_markets()) == 2


def test_auth_rate_limit(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "auth_rate_limit_per_minute", 2)
    for _ in range(2):
        client.post("/auth/login", json={"email": "nobody@test.com", "password": "password12"})
    r = client.post("/auth/login", json={"email": "nobody@test.com", "password": "password12"})
    assert r.status_code == 429
    for key in list(cache._memory):
        if key.startswith("rl:auth:"):
            cache.cache_delete(key)
