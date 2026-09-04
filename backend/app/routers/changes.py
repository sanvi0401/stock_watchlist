from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import DetectedChange, User
from app.schemas import HistoryItem, HistoryPage

router = APIRouter(prefix="/changes", tags=["changes"])


@router.get("/history", response_model=HistoryPage)
def history(
    severity: str | None = Query(default=None),
    cursor: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(DetectedChange).where(DetectedChange.user_id == user.id)
    if severity and severity.upper() != "ALL":
        mapping = {
            "HIGH": "HIGH",
            "HIGH_SIGNIFICANCE": "HIGH",
            "MEANINGFUL": "MEANINGFUL",
            "NOTABLE": "NOTABLE",
            "STABLE": "STABLE",
        }
        stmt = stmt.where(DetectedChange.severity == mapping.get(severity.upper(), severity.upper()))
    if cursor:
        stmt = stmt.where(DetectedChange.id < cursor)
    stmt = stmt.order_by(DetectedChange.detected_at.desc(), DetectedChange.id.desc()).limit(limit + 1)
    rows = list(db.scalars(stmt).all())
    next_cursor = None
    if len(rows) > limit:
        next_cursor = rows[limit].id
        rows = rows[:limit]
    return HistoryPage(
        items=[
            HistoryItem(
                id=r.id,
                timestamp=r.detected_at,
                symbol=r.symbol,
                change_type=r.change_type,
                significance_score=r.significance_score,
                severity=r.severity,  # type: ignore[arg-type]
                explanation=r.explanation,
                snapshot_id=r.snapshot_id,
            )
            for r in rows
        ],
        next_cursor=next_cursor,
    )
