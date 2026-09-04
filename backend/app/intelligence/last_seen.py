from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.intelligence.explanation import explain_change
from app.intelligence.significance import notable_floor, significance_score
from app.market.types import NormalizedQuote
from app.models import DetectedChange, Notification, UserStockState


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
    fingerprint: str = ""
    volatility_units: float = 0.0
    components: dict = field(default_factory=dict)


def _pct(new: float, old: float) -> float:
    if old == 0:
        return 0.0
    return (new - old) / old * 100.0


def _returns(closes: list[float]) -> list[float]:
    out: list[float] = []
    for i in range(1, len(closes)):
        if closes[i - 1]:
            out.append((closes[i] - closes[i - 1]) / closes[i - 1])
    return out


def change_fingerprint(user_id: int, symbol: str, baseline: float | None, current: float, snapshot_id: int | None) -> str:
    raw = f"{user_id}|{symbol}|{round(baseline or 0, 4)}|{round(current, 4)}|{snapshot_id or 0}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _baseline_price(state: UserStockState | None, quote: NormalizedQuote, lookback_mode: str) -> float | None:
    if lookback_mode == "previous_close":
        return quote.previous_close
    if lookback_mode == "five_day":
        closes = quote.recent_closes or quote.sparkline
        if len(closes) >= 5:
            return float(closes[-5])
        return state.last_seen_price if state else None
    if state is None:
        return None
    return state.last_seen_price


def calculate_change(
    quote: NormalizedQuote,
    state: UserStockState | None,
    snapshot_id: int | None,
    *,
    user_id: int,
    sensitivity: str = "balanced",
    lookback_mode: str = "since_last_check",
    emphasize_volume: bool = True,
) -> ChangeResult:
    now = datetime.now(UTC)
    day_pct = _pct(quote.price, quote.previous_close)
    volume_ratio = (quote.volume / quote.average_volume) if quote.average_volume else 1.0
    rets = _returns(quote.recent_closes or quote.sparkline)

    if state is None and lookback_mode == "since_last_check":
        change_type, explanation, evidence = explain_change(
            quote.symbol, 0, volume_ratio, quote.volatility, "STABLE", True, quote.data_status
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
            fingerprint=change_fingerprint(user_id, quote.symbol, None, quote.price, snapshot_id),
        )

    previous_price = _baseline_price(state, quote, lookback_mode)
    if previous_price is None:
        change_type, explanation, evidence = explain_change(
            quote.symbol, 0, volume_ratio, quote.volatility, "STABLE", True, quote.data_status
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
            fingerprint=change_fingerprint(user_id, quote.symbol, None, quote.price, snapshot_id),
        )

    if quote.data_status == "UNAVAILABLE":
        change_type, explanation, evidence = explain_change(
            quote.symbol, 0, volume_ratio, quote.volatility, "STABLE", False, "UNAVAILABLE"
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
            fingerprint=change_fingerprint(user_id, quote.symbol, previous_price, previous_price, snapshot_id),
        )

    since_pct = _pct(quote.price, previous_price)
    scored = significance_score(
        since_pct,
        quote.volatility,
        quote.volume,
        quote.average_volume,
        daily_returns=rets,
        sensitivity=sensitivity,
        emphasize_volume=emphasize_volume,
    )
    change_type, explanation, evidence = explain_change(
        quote.symbol,
        since_pct,
        volume_ratio,
        quote.volatility,
        scored["severity"],
        False,
        quote.data_status,
        volatility_units=scored.get("volatility_units"),
        regime_label=scored.get("regime_label"),
    )
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
        fingerprint=change_fingerprint(user_id, quote.symbol, previous_price, quote.price, snapshot_id),
        volatility_units=float(scored.get("volatility_units") or 0),
        components=scored.get("components") or {},
    )


def compare_and_record(
    db: Session,
    user_id: int,
    quote: NormalizedQuote,
    snapshot_id: int | None,
    *,
    commit_last_seen: bool = False,
    sensitivity: str = "balanced",
    lookback_mode: str = "since_last_check",
    persist_history: bool = False,
    emphasize_volume: bool = True,
    state: UserStockState | None = None,
) -> ChangeResult:
    """Calculate vs acknowledged baseline. GET must not pass commit_last_seen=True."""
    if state is None:
        state = (
            db.query(UserStockState)
            .filter(UserStockState.user_id == user_id, UserStockState.symbol == quote.symbol)
            .one_or_none()
        )
    result = calculate_change(
        quote,
        state,
        snapshot_id,
        user_id=user_id,
        sensitivity=sensitivity,
        lookback_mode=lookback_mode,
        emphasize_volume=emphasize_volume,
    )
    if persist_history and not result.first_seen and result.significance_score >= notable_floor(sensitivity):
        record_detected_change(db, user_id, result)
    if commit_last_seen and quote.data_status != "UNAVAILABLE":
        acknowledge_quote(db, user_id, quote, snapshot_id)
    return result


def record_detected_change(db: Session, user_id: int, result: ChangeResult) -> bool:
    if not result.fingerprint or result.first_seen:
        return False
    exists = db.query(DetectedChange).filter_by(user_id=user_id, fingerprint=result.fingerprint).one_or_none()
    if exists:
        return False
    db.add(
        DetectedChange(
            user_id=user_id,
            symbol=result.symbol,
            change_type=result.change_type,
            significance_score=result.significance_score,
            severity=result.severity,
            explanation=result.explanation,
            evidence=" | ".join(result.evidence),
            fingerprint=result.fingerprint,
            snapshot_id=result.snapshot_id,
        )
    )
    return True


def record_notification(db: Session, user_id: int, result: ChangeResult) -> bool:
    if result.first_seen or result.severity not in {"HIGH", "MEANINGFUL"}:
        return False
    exists = db.query(Notification).filter_by(user_id=user_id, fingerprint=result.fingerprint).one_or_none()
    if exists:
        return False
    db.add(
        Notification(
            user_id=user_id,
            title=f"{result.symbol} · {result.severity.title()}",
            body=result.explanation,
            kind="change",
            fingerprint=result.fingerprint,
        )
    )
    return True


def acknowledge_quote(db: Session, user_id: int, quote: NormalizedQuote, snapshot_id: int | None) -> None:
    if quote.data_status == "UNAVAILABLE":
        return
    now = datetime.now(UTC)
    state = (
        db.query(UserStockState)
        .filter(UserStockState.user_id == user_id, UserStockState.symbol == quote.symbol)
        .one_or_none()
    )
    if state is None:
        db.add(
            UserStockState(
                user_id=user_id,
                symbol=quote.symbol,
                last_seen_at=now,
                last_seen_price=quote.price,
                reference_snapshot_id=snapshot_id,
            )
        )
        return
    state.last_seen_at = now
    state.last_seen_price = quote.price
    if snapshot_id:
        state.reference_snapshot_id = snapshot_id
