from datetime import UTC, datetime, timedelta

from app.market.freshness import classify_freshness, market_state
from app.market.mock import MockMarketDataProvider
from app.market.service import _validate
from tests.conftest import auth_headers, client


def test_malformed_quotes_rejected():
    q = MockMarketDataProvider().get_quote("NVDA")
    q.price = 0
    assert _validate(q) is None
    q = MockMarketDataProvider().get_quote("NVDA")
    q.previous_close = float("nan")
    assert _validate(q) is None
    assert _validate(None) is None


def test_validate_normalises_bad_fields():
    q = MockMarketDataProvider().get_quote("NVDA")
    q.volatility = 5.0
    q.average_volume = 0
    q.timestamp = datetime.now(UTC) + timedelta(days=1)
    out = _validate(q)
    assert out.volatility == 0.02
    assert out.average_volume == out.volume
    assert out.timestamp <= datetime.now(UTC)


def test_market_state_by_clock():
    assert market_state(datetime(2026, 9, 5, 15, 0, tzinfo=UTC)) == "CLOSED"  # Saturday
    assert market_state(datetime(2026, 9, 8, 15, 0, tzinfo=UTC)) == "OPEN"  # Tue 11:00 ET
    assert market_state(datetime(2026, 9, 8, 11, 0, tzinfo=UTC)) == "PRE_MARKET"  # Tue 07:00 ET
    assert market_state(datetime(2026, 9, 8, 21, 0, tzinfo=UTC)) == "CLOSED"  # Tue 17:00 ET


def test_freshness_rules():
    open_now = datetime(2026, 9, 8, 15, 0, tzinfo=UTC)
    closed_now = datetime(2026, 9, 8, 22, 0, tzinfo=UTC)
    assert classify_freshness(open_now - timedelta(minutes=1), "LIVE", now=open_now) == "LIVE"
    assert classify_freshness(open_now - timedelta(minutes=10), "DELAYED", now=open_now) == "DELAYED"
    assert classify_freshness(open_now - timedelta(hours=2), "DELAYED", now=open_now) == "STALE"
    assert classify_freshness(closed_now - timedelta(hours=6), "DELAYED", now=closed_now) == "DELAYED"
    assert classify_freshness(open_now, "DELAYED", now=open_now, fallback=True) == "STALE"
    assert classify_freshness(open_now, "UNAVAILABLE", now=open_now) == "UNAVAILABLE"


def test_partial_dashboard_survives_unknown_symbol():
    h = auth_headers()
    created = client.post("/watchlists", json={"name": "Mixed", "symbols": ["NVDA", "AAPL"]}, headers=h)
    assert created.status_code == 201
    dash = client.get("/dashboard", headers=h)
    assert dash.status_code == 200
    assert dash.json()["stocks_tracked"] == 2


def test_session_timestamp_for_daily_bars():
    from app.market.freshness import session_timestamp

    now = datetime(2026, 9, 8, 15, 0, tzinfo=UTC)  # Tuesday 11:00 ET, market open
    today_bar = datetime(2026, 9, 8, 4, 0, tzinfo=UTC)  # yfinance stamps today's bar at midnight ET
    assert session_timestamp(today_bar, now) == now
    friday_bar = datetime(2026, 9, 4, 13, 30, tzinfo=UTC)
    assert session_timestamp(friday_bar, now) == datetime(2026, 9, 4, 20, 0, tzinfo=UTC)  # 16:00 ET
    assert classify_freshness(session_timestamp(friday_bar, now), "DELAYED", now=now) == "STALE"
    weekend = datetime(2026, 9, 6, 15, 0, tzinfo=UTC)
    assert classify_freshness(session_timestamp(friday_bar, weekend), "DELAYED", now=weekend) == "DELAYED"
