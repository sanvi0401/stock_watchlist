from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.intelligence.last_seen import checkpoint, compare_and_record, load_states
from app.market.mock import MockMarketDataProvider
from app.models import DetectedChange, User, UserStockState
from app.security import hash_password
from tests.conftest import TestingSession


def _user(db):
    user = User(name="T", email=f"u{uuid4().hex}@t.com", password_hash=hash_password("password12"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _state(db, user_id, symbol, price, ago: timedelta):
    then = datetime.now(UTC) - ago
    db.add(
        UserStockState(
            user_id=user_id, symbol=symbol, baseline_at=then, baseline_price=price,
            last_seen_at=then, last_seen_price=price,
        )
    )
    db.commit()


def test_first_time_stock_claims_no_change():
    db = TestingSession()
    user = _user(db)
    quote = MockMarketDataProvider().get_quote("NVDA")
    result = compare_and_record(db, user.id, quote, None, commit_last_seen=True)
    db.commit()
    assert result.first_seen is True
    assert result.since_last_check_percent is None
    assert "baseline" in result.explanation.lower()
    assert "up" not in result.explanation.lower().split()
    state = load_states(db, user.id)["NVDA"]
    assert state.baseline_price == quote.price == state.last_seen_price


def test_increase_and_decrease_direction():
    quote = MockMarketDataProvider().get_quote("NVDA")
    db = TestingSession()
    user = _user(db)
    _state(db, user.id, "NVDA", 100, timedelta(hours=1))
    up = compare_and_record(db, user.id, quote, None, commit_last_seen=False)
    assert up.since_last_check_percent and up.since_last_check_percent > 0
    assert up.previous_price == 100
    user2 = _user(db)
    _state(db, user2.id, "NVDA", 400, timedelta(hours=1))
    down = compare_and_record(db, user2.id, quote, None, commit_last_seen=False)
    assert down.since_last_check_percent and down.since_last_check_percent < 0


def test_unchanged_price_is_stable():
    db = TestingSession()
    user = _user(db)
    quote = MockMarketDataProvider().get_quote("AMZN")
    _state(db, user.id, "AMZN", quote.price, timedelta(hours=1))
    result = compare_and_record(db, user.id, quote, None, commit_last_seen=False)
    assert result.since_last_check_percent == 0
    assert result.severity == "STABLE"


def test_unavailable_preserves_previous_state():
    db = TestingSession()
    user = _user(db)
    _state(db, user.id, "NVDA", 120, timedelta(hours=1))
    quote = MockMarketDataProvider(force_status="UNAVAILABLE").get_quote("NVDA")
    result = compare_and_record(db, user.id, quote, None, commit_last_seen=True)
    db.commit()
    assert result.data_status == "UNAVAILABLE"
    assert result.current_price == 120
    assert result.since_last_check_percent is None
    state = load_states(db, user.id)["NVDA"]
    assert state.last_seen_price == 120 and state.baseline_price == 120


def test_refresh_within_visit_keeps_baseline():
    """Two dashboard loads a few seconds apart must show the same 'since last check'."""
    db = TestingSession()
    user = _user(db)
    quote = MockMarketDataProvider().get_quote("NVDA")
    _state(db, user.id, "NVDA", 100, timedelta(hours=3))
    first = compare_and_record(db, user.id, quote, None, commit_last_seen=True)
    db.commit()
    second = compare_and_record(db, user.id, quote, None, commit_last_seen=True)
    db.commit()
    assert first.new_visit is True
    assert second.new_visit is False
    assert first.since_last_check_percent == second.since_last_check_percent
    assert first.since_last_check_percent and first.since_last_check_percent > 0


def test_new_visit_rolls_baseline_forward():
    db = TestingSession()
    user = _user(db)
    quote = MockMarketDataProvider().get_quote("NVDA")
    _state(db, user.id, "NVDA", 100, timedelta(hours=3))
    compare_and_record(db, user.id, quote, None, commit_last_seen=True)
    db.commit()
    # Simulate the next visit an hour later.
    later = datetime.now(UTC) + timedelta(hours=1)
    again = compare_and_record(db, user.id, quote, None, commit_last_seen=True, now=later)
    db.commit()
    assert again.new_visit is True
    assert again.previous_price == quote.price
    assert again.since_last_check_percent == 0


def test_change_ledger_written_once_per_visit():
    db = TestingSession()
    user = _user(db)
    quote = MockMarketDataProvider().get_quote("NVDA")
    _state(db, user.id, "NVDA", 100, timedelta(hours=3))
    for _ in range(3):
        compare_and_record(db, user.id, quote, None, commit_last_seen=True)
        db.commit()
    rows = db.query(DetectedChange).filter_by(user_id=user.id, symbol="NVDA").count()
    assert rows == 1


def test_read_only_never_moves_baseline():
    db = TestingSession()
    user = _user(db)
    quote = MockMarketDataProvider().get_quote("NVDA")
    _state(db, user.id, "NVDA", 100, timedelta(hours=3))
    compare_and_record(db, user.id, quote, None, commit_last_seen=False)
    db.commit()
    state = load_states(db, user.id)["NVDA"]
    assert state.baseline_price == 100 and state.last_seen_price == 100


def test_checkpoint_resets_every_baseline():
    db = TestingSession()
    user = _user(db)
    provider = MockMarketDataProvider()
    _state(db, user.id, "NVDA", 100, timedelta(hours=3))
    quotes = [(provider.get_quote("NVDA"), None), (provider.get_quote("AAPL"), None)]
    assert checkpoint(db, user.id, quotes) == 2
    db.commit()
    states = load_states(db, user.id)
    assert states["NVDA"].baseline_price == quotes[0][0].price
    assert states["AAPL"].baseline_price == quotes[1][0].price
    result = compare_and_record(db, user.id, quotes[0][0], None, commit_last_seen=False)
    assert result.since_last_check_percent == 0


def test_lookback_modes():
    db = TestingSession()
    user = _user(db)
    quote = MockMarketDataProvider().get_quote("NVDA")
    _state(db, user.id, "NVDA", 100, timedelta(hours=3))
    prev_close = compare_and_record(db, user.id, quote, None, commit_last_seen=False, lookback_mode="previous_close")
    assert prev_close.previous_price == quote.previous_close
    five = compare_and_record(db, user.id, quote, None, commit_last_seen=False, lookback_mode="five_day")
    assert five.previous_price == quote.sparkline[-6]


def test_sqlite_naive_datetimes_do_not_crash():
    db = TestingSession()
    user = _user(db)
    naive = datetime.now() - timedelta(hours=2)
    db.add(UserStockState(user_id=user.id, symbol="AAPL", baseline_at=naive, baseline_price=200,
                          last_seen_at=naive, last_seen_price=200))
    db.commit()
    result = compare_and_record(db, user.id, MockMarketDataProvider().get_quote("AAPL"), None)
    assert result.since_last_check_percent is not None
