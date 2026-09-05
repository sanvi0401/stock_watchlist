from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import DetectedChange, MarketSnapshot, User
from app.schemas import HistoryItem, HistoryPage

router = APIRouter(prefix="/changes", tags=["changes"])
SEVERITIES = {"HIGH", "MEANINGFUL", "NOTABLE", "STABLE"}


def _pct(new: float, old: float) -> float:
    if old == 0:
        return 0.0
    return (new - old) / old * 100.0


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
    stmt = select(DetectedChange, MarketSnapshot).outerjoin(
        MarketSnapshot, DetectedChange.snapshot_id == MarketSnapshot.id
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

    rows = list(stmt.order_by(DetectedChange.id.desc()).limit(limit + 1).all())
    page_rows = rows[:limit]
    next_cursor = page_rows[-1][0].id if len(rows) > limit else None

    items: list[HistoryItem] = []
    for change, snapshot in page_rows:
        baseline = change.baseline_price
        current = change.current_price
        since_pct = change.since_last_check_percent
        if (baseline is None or current is None or since_pct is None) and snapshot is not None:
            baseline = snapshot.previous_close if baseline is None else baseline
            current = snapshot.price if current is None else current
            since_pct = _pct(current, baseline) if since_pct is None else since_pct
        if baseline is None or current is None or since_pct is None:
            continue
        items.append(
            HistoryItem(
                id=change.id,
                timestamp=change.detected_at,
                symbol=change.symbol,
                change_type=change.change_type,
                significance_score=change.significance_score,
                severity=change.severity,  # type: ignore[arg-type]
                baseline_price=baseline,
                current_price=current,
                currency=change.currency or user.currency or "USD",
                since_last_check_percent=since_pct,
                explanation=change.explanation,
                evidence=[e for e in (change.evidence or "").split(" | ") if e],
                snapshot_id=change.snapshot_id,
            )
        )

    return HistoryPage(items=items, next_cursor=next_cursor)
