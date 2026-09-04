"""Background refresh of every watched symbol.

Runs once per interval for the whole deployment, so provider load grows with
the number of *distinct symbols*, not with users × symbols. Individual
requests then hit the cache or the shared snapshot table.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import distinct, select

from app.db import SessionLocal
from app.market.service import market_service, prune_snapshots
from app.models import WatchlistStock

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def refresh_watched_symbols() -> None:
    db = SessionLocal()
    try:
        symbols = list(db.scalars(select(distinct(WatchlistStock.symbol))).all())
        if symbols:
            market_service.refresh_symbols(db, symbols)
    except Exception:  # noqa: BLE001
        logger.exception("snapshot refresh failed")
        db.rollback()
    finally:
        db.close()


def prune_old_snapshots() -> None:
    db = SessionLocal()
    try:
        removed = prune_snapshots(db)
        if removed:
            logger.info("pruned %d old market snapshots", removed)
    except Exception:  # noqa: BLE001
        logger.exception("snapshot prune failed")
        db.rollback()
    finally:
        db.close()


def start_scheduler(interval_seconds: int) -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        refresh_watched_symbols, "interval", seconds=interval_seconds, id="quotes", max_instances=1, coalesce=True
    )
    scheduler.add_job(prune_old_snapshots, "interval", hours=6, id="prune", max_instances=1, coalesce=True)
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
