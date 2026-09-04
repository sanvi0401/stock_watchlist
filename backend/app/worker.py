import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.db import SessionLocal
from app.market.service import market_service
from app.models import WatchlistStock

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def refresh_watched_symbols() -> None:
    db = SessionLocal()
    try:
        symbols = list({row.symbol for row in db.scalars(select(WatchlistStock)).all()})
        if symbols:
            market_service.refresh_symbols(db, symbols)
    except Exception:  # noqa: BLE001
        logger.exception("snapshot refresh failed")
    finally:
        db.close()


def start_scheduler(interval_seconds: int) -> None:
    if scheduler.running:
        return
    scheduler.add_job(refresh_watched_symbols, "interval", seconds=interval_seconds, id="quotes")
    scheduler.start()
