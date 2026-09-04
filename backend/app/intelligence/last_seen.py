from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.intelligence.explanation import explain_change
from app.intelligence.significance import significance_score
from app.market.types import NormalizedQuote
from app.models import DetectedChange, UserStockState


@dataclass
class ChangeResult:
    symbol: str
    current_price: float
    previous_price: float | None
    price_change_percent: float
    since_last_check_percent: float | None
    significance_score: float
    severity: str
    explanation: str
    change_type: str
    evidence: list[str]
    detected_at: datetime
    data_status: str
    first_seen: bool
    snapshot_id: int | None


def _pct(new: float, old: float) -> float:
    if old == 0:
        return 0.0
    return (new - old) / old * 100.0


def compare_and_record(
    db: Session,
    user_id: int,
    quote: NormalizedQuote,
    snapshot_id: int | None,
    *,
    commit_last_seen: bool = True,
    in_primary_watchlist: bool = True,
) -> ChangeResult:
    now = datetime.now(UTC)
    state = (
        db.query(UserStockState)
        .filter(UserStockState.user_id == user_id, UserStockState.symbol == quote.symbol)
        .one_or_none()
    )

    day_pct = _pct(quote.price, quote.previous_close)
    volume_ratio = (quote.volume / quote.average_volume) if quote.average_volume else 1.0

    if state is None:
        change_type, explanation, evidence = explain_change(
            quote.symbol, 0, volume_ratio, quote.volatility, "STABLE", True, quote.data_status
        )
        if commit_last_seen and quote.data_status != "UNAVAILABLE":
            db.add(
                UserStockState(
                    user_id=user_id,
                    symbol=quote.symbol,
                    last_seen_at=now,
                    last_seen_price=quote.price,
                    reference_snapshot_id=snapshot_id,
                )
            )
        return ChangeResult(
            symbol=quote.symbol,
            current_price=quote.price,
            previous_price=None,
            price_change_percent=round(day_pct, 2),
            since_last_check_percent=None,
            significance_score=0,
            severity="STABLE",
            explanation=explanation,
            change_type=change_type,
            evidence=evidence,
            detected_at=now,
            data_status=quote.data_status,
            first_seen=True,
            snapshot_id=snapshot_id,
        )

    previous_price = state.last_seen_price
    since_pct = _pct(quote.price, previous_price)

    if quote.data_status == "UNAVAILABLE":
        change_type, explanation, evidence = explain_change(
            quote.symbol, since_pct, volume_ratio, quote.volatility, "STABLE", False, "UNAVAILABLE"
        )
        return ChangeResult(
            symbol=quote.symbol,
            current_price=previous_price,
            previous_price=previous_price,
            price_change_percent=round(day_pct, 2),
            since_last_check_percent=0.0,
            significance_score=0,
            severity="STABLE",
            explanation=explanation,
            change_type=change_type,
            evidence=evidence,
            detected_at=now,
            data_status="UNAVAILABLE",
            first_seen=False,
            snapshot_id=snapshot_id,
        )

    scored = significance_score(
        since_pct,
        quote.volatility,
        quote.volume,
        quote.average_volume,
        in_primary_watchlist=in_primary_watchlist,
    )
    change_type, explanation, evidence = explain_change(
        quote.symbol,
        since_pct,
        volume_ratio,
        quote.volatility,
        scored["severity"],
        False,
        quote.data_status,
    )

    if scored["score"] >= 30:
        db.add(
            DetectedChange(
                user_id=user_id,
                symbol=quote.symbol,
                change_type=change_type,
                significance_score=scored["score"],
                severity=scored["severity"],
                explanation=explanation,
                evidence=" | ".join(evidence),
                detected_at=now,
                snapshot_id=snapshot_id,
            )
        )

    if commit_last_seen:
        state.last_seen_at = now
        state.last_seen_price = quote.price
        if snapshot_id:
            state.reference_snapshot_id = snapshot_id

    return ChangeResult(
        symbol=quote.symbol,
        current_price=quote.price,
        previous_price=previous_price,
        price_change_percent=round(day_pct, 2),
        since_last_check_percent=round(since_pct, 2),
        significance_score=scored["score"],
        severity=scored["severity"],
        explanation=explanation,
        change_type=change_type,
        evidence=evidence,
        detected_at=now,
        data_status=quote.data_status,
        first_seen=False,
        snapshot_id=snapshot_id,
    )
