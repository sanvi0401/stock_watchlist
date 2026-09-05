import time
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from app.config import Settings, validate_settings
from app.intelligence.last_seen import change_fingerprint, compare_and_record
from app.intelligence.significance import significance_score, volatility_units
from app.market.calendar import classify_quote_status
from app.market.mock import MockMarketDataProvider
from app.market.service import MarketDataService
from app.models import DetectedChange, MarketSnapshot, Notification, UserStockState
from tests.conftest import TestingSession, auth_headers, client


def test_production_refuses_insecure_secret():
    cfg = Settings(
        environment="production",
        secret_key="dev-change-me-in-production",
        database_url="postgresql+psycopg2://u:p@localhost/db",
    )
    with pytest.raises(SystemExit):
        validate_settings(cfg)


def test_production_refuses_sqlite():
    cfg = Settings(
        environment="production",
        secret_key="a" * 32,
        database_url="sqlite+pysqlite:////tmp/marketwatch.db",
    )
    with pytest.raises(SystemExit):
        validate_settings(cfg)


def test_production_forgot_password_never_echoes_token():
    from unittest.mock import MagicMock

    from app.config import settings as live

    email = "prodreset@test.com"
    client.post("/auth/register", json={"name": "P", "email": email, "password": "password12"})
    mock = MagicMock(wraps=live)
    mock.allow_dev_reset_echo = False
    with patch("app.routers.auth.get_settings", return_value=mock):
        r = client.post("/auth/forgot-password", json={"email": email})
    assert r.status_code == 200
    body = r.json()
    assert body.get("dev_reset_token") is None
    assert "reset_url" not in body or body.get("reset_url") is None
    assert "token=" not in str(body)


def test_memory_cache_expires():
    from unittest.mock import patch

    from app.cache import _memory, cache_get, cache_set

    with patch("app.cache.get_redis", return_value=None):
        cache_set("ttl-key", {"v": 1}, ttl=30)
        assert cache_get("ttl-key") == {"v": 1}
        payload, _ = _memory["ttl-key"]
        _memory["ttl-key"] = (payload, time.time() - 1)
        assert cache_get("ttl-key") is None
        assert "ttl-key" not in _memory


def test_delayed_ages_to_stale():
    now = datetime.now(UTC)
    old = now - timedelta(hours=2)
    assert classify_quote_status("DELAYED", old, now=now) == "STALE"
    assert classify_quote_status("LIVE", now - timedelta(seconds=10), now=now) == "LIVE"
    assert classify_quote_status("LIVE", now - timedelta(minutes=10), now=now) == "DELAYED"


def test_provider_failure_uses_persisted_snapshot_not_mock():
    from app.cache import cache_delete
    from app.config import settings as live

    db = TestingSession()
    ts = datetime.now(UTC) - timedelta(hours=3)
    snap = MarketSnapshot(
        symbol="FAILX",
        company_name="Fail Co",
        price=150.0,
        previous_close=148.0,
        volume=10,
        average_volume=10,
        volatility=0.02,
        timestamp=ts,
        source="yfinance",
        data_status="DELAYED",
        market_state="CLOSED",
        sparkline="[148,150]",
    )
    db.add(snap)
    db.commit()
    cache_delete(f"quote:{live.market_data_provider}:FAILX")

    class Boom:
        def get_quote(self, _symbol):
            raise RuntimeError("yahoo down")

        def get_quotes(self, symbols):
            raise RuntimeError("yahoo down")

        def search(self, _q):
            return []

        def get_history(self, _s, _r):
            return []

    svc = MarketDataService()
    svc.provider = Boom()
    quote, stored = svc.get_quote(db, "FAILX")
    assert stored is not None
    assert quote is not None
    assert quote.source != "mock-terminal"
    assert quote.price == 150.0
    assert quote.data_status == "STALE"


def test_unavailable_when_no_snapshot_and_provider_fails():
    db = TestingSession()

    class Boom:
        def get_quote(self, _symbol):
            return None

        def get_quotes(self, symbols):
            return {s: None for s in symbols}

        def search(self, _q):
            return []

        def get_history(self, _s, _r):
            return []

    svc = MarketDataService()
    svc.provider = Boom()
    quote, stored = svc.get_quote(db, "ZZZZ")
    assert quote is None
    assert stored is None


def test_repeated_dashboard_does_not_advance_baseline_or_duplicate_changes():
    h = auth_headers()
    client.post("/watchlists", json={"name": "Tech", "symbols": ["NVDA"]}, headers=h)
    first = client.get("/dashboard", headers=h)
    assert first.status_code == 200
    db = TestingSession()
    # sanvi@test.com from auth_headers
    from app.models import User

    user = db.query(User).filter_by(email="sanvi@test.com").one()
    before = db.query(UserStockState).filter_by(user_id=user.id, symbol="NVDA").one()
    price_before = before.last_seen_price
    changes_before = db.query(DetectedChange).filter_by(user_id=user.id).count()
    notes_before = db.query(Notification).filter_by(user_id=user.id).count()
    db.close()

    second = client.get("/dashboard", headers=h)
    assert second.status_code == 200
    db = TestingSession()
    user = db.query(User).filter_by(email="sanvi@test.com").one()
    after = db.query(UserStockState).filter_by(user_id=user.id, symbol="NVDA").one()
    assert after.last_seen_price == price_before
    assert db.query(DetectedChange).filter_by(user_id=user.id).count() == changes_before
    assert db.query(Notification).filter_by(user_id=user.id).count() == notes_before
    db.close()

    ack = client.post("/dashboard/acknowledge", headers=h)
    assert ack.status_code == 200
    db = TestingSession()
    user = db.query(User).filter_by(email="sanvi@test.com").one()
    seen = db.query(UserStockState).filter_by(user_id=user.id, symbol="NVDA").one()
    assert seen.last_seen_price == pytest.approx(172.38)
    db.close()


def test_stock_detail_does_not_write_detected_change():
    h = auth_headers()
    client.post("/watchlists", json={"name": "X", "symbols": ["AAPL"]}, headers=h)
    db = TestingSession()
    from app.models import User

    user = db.query(User).filter_by(email="sanvi@test.com").one()
    n0 = db.query(DetectedChange).filter_by(user_id=user.id, symbol="AAPL").count()
    db.close()
    r = client.get("/stocks/AAPL", headers=h)
    assert r.status_code == 200
    db = TestingSession()
    user = db.query(User).filter_by(email="sanvi@test.com").one()
    assert db.query(DetectedChange).filter_by(user_id=user.id, symbol="AAPL").count() == n0
    db.close()


def test_history_ranges_return_real_points():
    h = auth_headers()
    five = client.get("/stocks/NVDA/history", params={"range": "5d"}, headers=h)
    assert five.status_code == 200
    assert len(five.json()) >= 2
    one = client.get("/stocks/NVDA/history", params={"range": "1d"}, headers=h)
    assert one.status_code == 200
    assert len(five.json()) != len(one.json())


def test_significance_is_volatility_standardized_not_zscore_claim():
    units = volatility_units(6.0, [0.01, -0.01, 0.012, -0.008, 0.009, 0.011], 0.02)
    assert units > 0
    scored = significance_score(6.0, 0.015, 80_000_000, 40_000_000, daily_returns=[0.01] * 20 + [0.04, -0.05, 0.06, -0.04, 0.05])
    assert "volatility_units" in scored
    assert scored["regime_label"] in {"elevated_short_vol", "typical_regime", "quiet_regime", "insufficient_history"}
    assert "user_relevance" not in scored["components"]


def test_volume_anomaly_zero_early_session():
    early = significance_score(0.2, 0.02, 90_000_000, 40_000_000, session_fraction=0.05)
    late = significance_score(0.2, 0.02, 90_000_000, 40_000_000, session_fraction=1.0)
    assert early["components"]["volume_anomaly"] == 0
    assert late["components"]["volume_anomaly"] > 0


def test_five_day_lookback_uses_fifth_close():
    db = TestingSession()
    from app.models import User
    from app.security import hash_password
    from uuid import uuid4

    user = User(name="T", email=f"f{uuid4().hex}@t.com", password_hash=hash_password("password12"))
    db.add(user)
    db.commit()
    db.refresh(user)
    quote = MockMarketDataProvider().get_quote("NVDA")
    closes = [100, 101, 102, 103, 104, 105, 106, 107]
    quote.recent_closes = closes
    db.add(UserStockState(user_id=user.id, symbol="NVDA", last_seen_at=datetime.now(UTC), last_seen_price=999))
    db.commit()
    result = compare_and_record(db, user.id, quote, None, lookback_mode="five_day", commit_last_seen=False)
    assert result.previous_price == 103.0


def test_fingerprint_stable():
    a = change_fingerprint(1, "NVDA", 100.0, 110.0, 7)
    b = change_fingerprint(1, "NVDA", 100.0, 110.0, 7)
    assert a == b
    assert a != change_fingerprint(1, "NVDA", 100.0, 111.0, 7)
