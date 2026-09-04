"""Shared quote path: cache TTL, provider failure fallback, conflict resolution."""

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app import cache
from app.market.mock import MockMarketDataProvider
from app.market.service import MarketDataService, latest_db_snapshot
from app.models import MarketSnapshot
from tests.conftest import TestingSession


def test_memory_cache_expires():
    cache.cache_set("k", {"a": 1}, ttl=1)
    assert cache.cache_get("k") == {"a": 1}
    with patch("app.cache.time.monotonic", return_value=time.monotonic() + 5):
        assert cache.cache_get("k") is None


def test_provider_failure_serves_last_snapshot_as_stale():
    db = TestingSession()
    service = MarketDataService()
    service.provider = MockMarketDataProvider()
    quote, snap = service.get_quote(db, "META")
    assert quote and snap
    db.commit()
    cache.cache_delete("quote:mock:META")

    class Broken:
        def get_quote(self, symbol):
            raise RuntimeError("provider down")

    service.provider = Broken()
    fallback, snap2 = service.get_quote(db, "META")
    assert fallback is not None
    assert fallback.data_status == "STALE"
    assert fallback.price == quote.price
    assert snap2.id == snap.id


def test_unknown_symbol_without_history_is_none():
    db = TestingSession()
    service = MarketDataService()
    service.provider = MockMarketDataProvider()
    assert service.get_quote(db, "NOPE99") == (None, None)


def test_older_provider_print_does_not_overwrite_newer_snapshot():
    db = TestingSession()
    service = MarketDataService()
    service.provider = MockMarketDataProvider()
    cache.cache_delete("quote:mock:CRM")
    newer = datetime.now(UTC) - timedelta(minutes=1)
    db.add(
        MarketSnapshot(
            symbol="CRM", company_name="Salesforce, Inc.", price=999.0, previous_close=990.0, volume=1, average_volume=1,
            volatility=0.02, timestamp=newer, source="test", provider_status="DELAYED",
        )
    )
    db.commit()

    class Lagging(MockMarketDataProvider):
        def get_quote(self, symbol):
            q = super().get_quote(symbol)
            q.timestamp = newer - timedelta(hours=3)
            return q

    service.provider = Lagging()
    quote, snap = service.get_quote(db, "CRM")
    assert quote.price == 999.0
    assert snap.price == 999.0
    assert db.query(MarketSnapshot).filter_by(symbol="CRM").count() == 1


def test_identical_print_does_not_duplicate_snapshot():
    db = TestingSession()
    service = MarketDataService()
    fixed = datetime.now(UTC) - timedelta(minutes=2)

    class Fixed(MockMarketDataProvider):
        def get_quote(self, symbol):
            q = super().get_quote(symbol)
            q.timestamp = fixed
            return q

    service.provider = Fixed()
    for _ in range(3):
        cache.cache_delete("quote:mock:COST")
        service.get_quote(db, "COST")
        db.commit()
    assert db.query(MarketSnapshot).filter_by(symbol="COST").count() == 1
    assert latest_db_snapshot(db, "COST").price == 918.40


def test_prune_keeps_newest_snapshot_per_symbol():
    from app.market.service import prune_snapshots

    db = TestingSession()
    old = datetime.now(UTC) - timedelta(days=30)
    for i, price in enumerate((1.0, 2.0)):
        db.add(
            MarketSnapshot(
                symbol="PRUNE", company_name="x", price=price, previous_close=1.0, timestamp=old + timedelta(hours=i),
                fetched_at=old + timedelta(hours=i), source="test",
            )
        )
    db.commit()
    removed = prune_snapshots(db, keep_days=7)
    assert removed == 1
    assert latest_db_snapshot(db, "PRUNE").price == 2.0
