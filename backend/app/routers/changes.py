from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import DetectedChange, User
from app.schemas import HistoryItem, HistoryPage

router = APIRouter(prefix="/changes", tags=["changes"])
SEVERITIES = {"HIGH", "MEANINGFUL", "NOTABLE", "STABLE"}


@router.get("/history", response_model=HistoryPage)
def history(
    severity: str | None = Query(default=None),
    symbol: str | None = Query(default=None, max_length=16),
    cursor: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Keyset-paginated ledger of recorded changes (newest first)."""
    stmt = select(DetectedChange).where(DetectedChange.user_id == user.id)
    if severity and severity.upper() in SEVERITIES:
        stmt = stmt.where(DetectedChange.severity == severity.upper())
    if symbol:
        stmt = stmt.where(DetectedChange.symbol == symbol.upper())
    if cursor:
        stmt = stmt.where(DetectedChange.id < cursor)
    rows = list(db.scalars(stmt.order_by(DetectedChange.id.desc()).limit(limit + 1)).all())
    next_cursor = rows[limit - 1].id if len(rows) > limit else None
    return HistoryPage(
        items=[
            HistoryItem(
                id=r.id,
                timestamp=r.detected_at,
                symbol=r.symbol,
                change_type=r.change_type,
                significance_score=r.significance_score,
                severity=r.severity,  # type: ignore[arg-type]
                baseline_price=r.baseline_price,
                current_price=r.current_price,
                currency=r.currency or "USD",
                since_last_check_percent=r.since_last_check_percent,
                explanation=r.explanation,
                evidence=[e for e in (r.evidence or "").split(" | ") if e],
                snapshot_id=r.snapshot_id,
            )
            for r in rows[:limit]
        ],
        next_cursor=next_cursor,
    )
