from datetime import UTC, datetime
from uuid import uuid4

from app.intelligence.last_seen import compare_and_record
from app.market.mock import MockMarketDataProvider
from app.models import User, UserStockState
from app.security import hash_password
from tests.conftest import TestingSession


def _user(db):
    user = User(name="T", email=f"u{uuid4().hex}@t.com", password_hash=hash_password("password12"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_first_time_stock():
    db = TestingSession()
    user = _user(db)
    quote = MockMarketDataProvider().get_quote("NVDA")
    result = compare_and_record(db, user.id, quote, None, commit_last_seen=True)
    db.commit()
    assert result.first_seen is True
    assert result.since_last_check_percent is None
    assert "baseline" in result.explanation.lower() or "added" in result.explanation.lower()


def test_price_increase_and_decrease():
    db = TestingSession()
    user = _user(db)
    quote = MockMarketDataProvider().get_quote("NVDA")
    db.add(UserStockState(user_id=user.id, symbol="NVDA", last_seen_at=datetime.now(UTC), last_seen_price=100))
    db.commit()
    up = compare_and_record(db, user.id, quote, None, commit_last_seen=False)
    assert up.since_last_check_percent and up.since_last_check_percent > 0
    db2 = TestingSession()
    user2 = _user(db2)
    db2.add(UserStockState(user_id=user2.id, symbol="NVDA", last_seen_at=datetime.now(UTC), last_seen_price=400))
    db2.commit()
    down = compare_and_record(db2, user2.id, quote, None, commit_last_seen=False)
    assert down.since_last_check_percent and down.since_last_check_percent < 0


def test_unchanged_price():
    db = TestingSession()
    user = _user(db)
    quote = MockMarketDataProvider().get_quote("AMZN")
    db.add(
        UserStockState(
            user_id=user.id, symbol="AMZN", last_seen_at=datetime.now(UTC), last_seen_price=quote.price
        )
    )
    db.commit()
    result = compare_and_record(db, user.id, quote, None, commit_last_seen=False)
    assert result.since_last_check_percent == 0
    assert result.severity == "STABLE"


def test_missing_previous_state_does_not_claim_change():
    db = TestingSession()
    user = _user(db)
    quote = MockMarketDataProvider().get_quote("COST")
    result = compare_and_record(db, user.id, quote, None)
    assert result.first_seen is True
    assert "increased" not in result.explanation.lower()


def test_unavailable_preserves_previous():
    db = TestingSession()
    user = _user(db)
    db.add(UserStockState(user_id=user.id, symbol="NVDA", last_seen_at=datetime.now(UTC), last_seen_price=120))
    db.commit()
    quote = MockMarketDataProvider(force_status="UNAVAILABLE").get_quote("NVDA")
    result = compare_and_record(db, user.id, quote, None, commit_last_seen=True)
    assert result.data_status == "UNAVAILABLE"
    assert result.current_price == 120
    state = db.query(UserStockState).filter_by(user_id=user.id, symbol="NVDA").one()
    assert state.last_seen_price == 120


def test_stale_is_not_live():
    quote = MockMarketDataProvider(force_status="STALE").get_quote("NVDA")
    assert quote.data_status == "STALE"


def test_double_commit_keeps_since_last_check_delta():
    db = TestingSession()
    user = _user(db)
    quote = MockMarketDataProvider().get_quote("NVDA")
    db.add(UserStockState(user_id=user.id, symbol="NVDA", last_seen_at=datetime.now(UTC), last_seen_price=100))
    db.commit()
    first = compare_and_record(db, user.id, quote, None, commit_last_seen=True)
    db.commit()
    second = compare_and_record(db, user.id, quote, None, commit_last_seen=True)
    assert first.since_last_check_percent and first.since_last_check_percent > 0
    assert second.since_last_check_percent == first.since_last_check_percent


def test_multiple_stocks():
    db = TestingSession()
    user = _user(db)
    for sym in ("NVDA", "AAPL", "COST"):
        q = MockMarketDataProvider().get_quote(sym)
        compare_and_record(db, user.id, q, None)
    db.commit()
    assert db.query(UserStockState).filter_by(user_id=user.id).count() == 3
