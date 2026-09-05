import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import DetectedChange, User
from app.schemas import HistoryItem, HistoryPage

router = APIRouter(prefix="/changes", tags=["changes"])
SEVERITIES = {"HIGH", "MEANINGFUL", "NOTABLE", "STABLE"}
logger = logging.getLogger(__name__)


@router.get("/history", response_model=HistoryPage)
def history(
    severity: str | None = Query(default=None),
    symbol: str | None = Query(default=None, max_length=16),
    cursor: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return recorded changes; an empty history is a normal empty response."""
    stmt = select(
        DetectedChange.id,
        DetectedChange.symbol,
        DetectedChange.change_type,
        DetectedChange.significance_score,
        DetectedChange.severity,
        DetectedChange.baseline_price,
        DetectedChange.current_price,
        DetectedChange.currency,
        DetectedChange.since_last_check_percent,
        DetectedChange.explanation,
        DetectedChange.evidence,
        DetectedChange.detected_at,
    ).where(DetectedChange.user_id == user.id)

    if severity:
        normalized = severity.strip().upper()
        if normalized not in SEVERITIES:
            return HistoryPage(items=[], next_cursor=None)
        stmt = stmt.where(DetectedChange.severity == normalized)
    if symbol:
        stmt = stmt.where(DetectedChange.symbol == symbol.strip().upper())
    if cursor:
        stmt = stmt.where(DetectedChange.id < cursor)

    try:
        rows = list(stmt.order_by(DetectedChange.id.desc()).limit(limit + 1).all())
    except ProgrammingError as exc:
        # A pre-existing Neon database can briefly have the old detected_changes
        # schema while the serverless startup migration catches up. Treat that
        # state as an empty history instead of surfacing a generic 500 to users.
        db.rollback()
        logger.warning("History schema is not ready yet: %s", exc)
        return HistoryPage(items=[], next_cursor=None)

    page_rows = rows[:limit]
    next_cursor = page_rows[-1][0] if len(rows) > limit else None

    items: list[HistoryItem] = []
    for row in page_rows:
        (
            change_id,
            change_symbol,
            change_type,
            significance_score,
            change_severity,
            baseline,
            current,
            stored_currency,
            since_pct,
            explanation,
            evidence,
            detected_at,
        ) = row

        if baseline is None or current is None:
            continue
        if since_pct is None:
            since_pct = 0.0 if baseline == 0 else (current - baseline) / baseline * 100.0

        items.append(
            HistoryItem(
                id=change_id,
                timestamp=detected_at,
                symbol=change_symbol,
                change_type=change_type,
                significance_score=significance_score,
                severity=change_severity,
                baseline_price=baseline,
                current_price=current,
                currency=stored_currency or user.currency or "USD",
                since_last_check_percent=since_pct,
                explanation=explanation,
                evidence=[e for e in (evidence or "").split(" | ") if e],
                snapshot_id=None,
            )
        )

    return HistoryPage(items=items, next_cursor=next_cursor)
