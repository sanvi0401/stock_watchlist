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
    """Keyset-paginated history that works with both legacy and upgraded databases."""
    # Only select columns that exist in the original detected_changes table.
    # This keeps existing Neon databases readable even before their optional
    # history columns have been added.
    stmt = select(
        DetectedChange.id,
        DetectedChange.user_id,
        DetectedChange.symbol,
        DetectedChange.change_type,
        DetectedChange.significance_score,
        DetectedChange.severity,
        DetectedChange.explanation,
        DetectedChange.evidence,
        DetectedChange.detected_at,
        DetectedChange.snapshot_id,
        MarketSnapshot,
    ).outerjoin(
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
    next_cursor = page_rows[-1][0] if len(rows) > limit else None

    items: list[HistoryItem] = []
    for row in page_rows:
        (
            change_id,
            _user_id,
            change_symbol,
            change_type,
            significance_score,
            change_severity,
            explanation,
            evidence,
            detected_at,
            snapshot_id,
            snapshot,
        ) = row

        # Legacy rows derive the display prices from their linked snapshot.
        baseline = snapshot.previous_close if snapshot is not None else None
        current = snapshot.price if snapshot is not None else None
        since_pct = _pct(current, baseline) if current is not None and baseline is not None else None
        if baseline is None or current is None or since_pct is None:
            continue

        items.append(
            HistoryItem(
                id=change_id,
                timestamp=detected_at,
                symbol=change_symbol,
                change_type=change_type,
                significance_score=significance_score,
                severity=change_severity,  # type: ignore[arg-type]
                baseline_price=baseline,
                current_price=current,
                currency=user.currency or "USD",
                since_last_check_percent=since_pct,
                explanation=explanation,
                evidence=[e for e in (evidence or "").split(" | ") if e],
                snapshot_id=snapshot_id,
            )
        )

    return HistoryPage(items=items, next_cursor=next_cursor)
