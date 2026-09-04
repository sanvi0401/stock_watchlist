"""The heart of the product: what changed for *this user* since *they* last looked.

Visit semantics
---------------
A "visit" is any dashboard activity within ``check_session_minutes``. Within
a visit the baseline stays put, so refreshing the page (or React Strict Mode
double-fetching) does not erase the comparison. When a new visit starts, the
baseline rolls forward to the price seen at the end of the previous visit.

State lives in the database (``UserStockState``), so it works across
processes, workers and devices. There is no in-memory state here.

Change ledger
-------------
A ``DetectedChange`` row is written once per visit per symbol, only when the
baseline actually rolls and the move clears the NOTABLE floor. Refreshing
does not duplicate history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.intelligence.explanation import explain_change
from app.intelligence.significance import notable_floor, significance_score
from app.market.freshness import as_utc
from app.market.types import NormalizedQuote
from app.models import DetectedChange, UserStockState

BASELINE_LABELS = {
    "since_last_check": "since you last checked",
    "previous_close": "since the previous close",
    "five_day": "over the last five sessions",
}


@dataclass
class ChangeResult:
    symbol: str
    current_price: float
    previous_price: float | None
    baseline_at: datetime | None
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
    new_visit: bool = False
    recorded_change: DetectedChange | None = field(default=None, repr=False)


def _pct(new: float, old: float | None) -> float:
    if not old:
        return 0.0
    return (new - old) / old * 100.0


def load_states(db: Session, user_id: int, symbols: list[str] | None = None) -> dict[str, UserStockState]:
    stmt = select(UserStockState).where(UserStockState.user_id == user_id)
    if symbols is not None:
        stmt = stmt.where(UserStockState.symbol.in_(symbols))
    return {row.symbol: row for row in db.scalars(stmt).all()}


def start_state(
    db: Session, user_id: int, symbol: str, price: float, snapshot_id: int | None, now: datetime | None = None
) -> UserStockState:
    """Create the first observation for (user, symbol). Safe under concurrent requests."""
    now = now or datetime.now(UTC)
    state = UserStockState(
        user_id=user_id,
        symbol=symbol,
        baseline_at=now,
        baseline_price=price,
        last_seen_at=now,
        last_seen_price=price,
        reference_snapshot_id=snapshot_id,
    )
    db.add(state)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError:
        # Another request inserted the same row a moment ago; use theirs.
        db.expire_all()
        existing = db.scalar(
            select(UserStockState).where(UserStockState.user_id == user_id, UserStockState.symbol == symbol)
        )
        if existing is None:
            raise
        return existing
    return state


def _is_same_visit(state: UserStockState, now: datetime) -> bool:
    last = as_utc(state.last_seen_at)
    return last is not None and now - last < timedelta(minutes=settings.check_session_minutes)


def compare_and_record(
    db: Session,
    user_id: int,
    quote: NormalizedQuote,
    snapshot_id: int | None,
    *,
    commit_last_seen: bool = True,
    state: UserStockState | None = None,
    states: dict[str, UserStockState] | None = None,
    sensitivity: str = "balanced",
    lookback_mode: str = "since_last_check",
    now: datetime | None = None,
) -> ChangeResult:
    """Compare the quote to the user's baseline and, if this is a viewing, advance last-seen.

    ``commit_last_seen=False`` is a pure read (watchlist tables, stock detail).
    ``commit_last_seen=True`` is a viewing (the Overview): the baseline rolls
    at the start of a new visit and last-seen is updated.
    """
    now = now or datetime.now(UTC)
    if state is None:
        if states is not None:
            state = states.get(quote.symbol)
        else:
            state = db.scalar(
                select(UserStockState).where(
                    UserStockState.user_id == user_id, UserStockState.symbol == quote.symbol
                )
            )

    day_pct = _pct(quote.price, quote.previous_close)
    volume_ratio = (quote.volume / quote.average_volume) if quote.average_volume else 1.0

    if state is None:
        change_type, explanation, evidence = explain_change(
            quote.symbol, 0, volume_ratio, quote.volatility, "STABLE", True, quote.data_status
        )
        if commit_last_seen and quote.data_status != "UNAVAILABLE":
            created = start_state(db, user_id, quote.symbol, quote.price, snapshot_id, now)
            if states is not None:
                states[quote.symbol] = created
        return ChangeResult(
            symbol=quote.symbol,
            current_price=quote.price,
            previous_price=None,
            baseline_at=None,
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

    new_visit = False
    if commit_last_seen and quote.data_status != "UNAVAILABLE" and not _is_same_visit(state, now):
        # New visit: what the user last saw becomes the thing we compare against.
        state.baseline_price = state.last_seen_price
        state.baseline_at = state.last_seen_at
        new_visit = True

    baseline_price = state.baseline_price
    baseline_at = as_utc(state.baseline_at)
    label = BASELINE_LABELS.get(lookback_mode, BASELINE_LABELS["since_last_check"])
    if lookback_mode == "previous_close":
        baseline_price = quote.previous_close
        baseline_at = None
    elif lookback_mode == "five_day" and len(quote.sparkline) >= 6:
        baseline_price = float(quote.sparkline[-6])
        baseline_at = None
    since_pct = _pct(quote.price, baseline_price)

    if quote.data_status == "UNAVAILABLE":
        change_type, explanation, evidence = explain_change(
            quote.symbol, 0, volume_ratio, quote.volatility, "STABLE", False, "UNAVAILABLE"
        )
        return ChangeResult(
            symbol=quote.symbol,
            current_price=state.last_seen_price,
            previous_price=baseline_price,
            baseline_at=baseline_at,
            price_change_percent=0.0,
            since_last_check_percent=None,
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
        since_pct, quote.volatility, quote.volume, quote.average_volume, sensitivity=sensitivity
    )
    change_type, explanation, evidence = explain_change(
        quote.symbol,
        since_pct,
        volume_ratio,
        quote.volatility,
        scored["severity"],
        False,
        quote.data_status,
        sigma=scored["sigma"],
        baseline_label=label,
    )

    recorded: DetectedChange | None = None
    if new_visit and scored["score"] >= notable_floor(sensitivity):
        recorded = DetectedChange(
            user_id=user_id,
            symbol=quote.symbol,
            change_type=change_type,
            significance_score=scored["score"],
            severity=scored["severity"],
            baseline_price=baseline_price,
            current_price=quote.price,
            currency=quote.currency,
            since_last_check_percent=round(since_pct, 2),
            explanation=explanation,
            evidence=" | ".join(evidence),
            detected_at=now,
            snapshot_id=snapshot_id,
        )
        db.add(recorded)

    if commit_last_seen:
        state.last_seen_at = now
        state.last_seen_price = quote.price
        if snapshot_id:
            state.reference_snapshot_id = snapshot_id

    return ChangeResult(
        symbol=quote.symbol,
        current_price=quote.price,
        previous_price=baseline_price,
        baseline_at=baseline_at,
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
        new_visit=new_visit,
        recorded_change=recorded,
    )


def checkpoint(db: Session, user_id: int, quotes: list[tuple[NormalizedQuote, int | None]], now: datetime | None = None) -> int:
    """User says "I'm caught up": every baseline becomes the current price."""
    now = now or datetime.now(UTC)
    states = load_states(db, user_id)
    count = 0
    for quote, snapshot_id in quotes:
        if quote.data_status == "UNAVAILABLE":
            continue
        state = states.get(quote.symbol)
        if state is None:
            start_state(db, user_id, quote.symbol, quote.price, snapshot_id, now)
        else:
            state.baseline_price = quote.price
            state.baseline_at = now
            state.last_seen_price = quote.price
            state.last_seen_at = now
            if snapshot_id:
                state.reference_snapshot_id = snapshot_id
        count += 1
    return count
