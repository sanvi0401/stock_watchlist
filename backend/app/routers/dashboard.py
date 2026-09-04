from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import get_current_user
from app.intelligence.last_seen import acknowledge_quote, compare_and_record, record_notification
from app.market.service import latest_snapshots_map, market_service
from app.models import User, UserSettings, UserStockState, Watchlist
from app.schemas import AcknowledgeOut, DashboardOut, QuoteOut

router = APIRouter(tags=["dashboard"])

SEVERITY_RANK = {"HIGH": 0, "MEANINGFUL": 1, "NOTABLE": 2, "STABLE": 3, "UNAVAILABLE": 4}


def _hour_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


def _unavailable(symbol: str, message: str) -> QuoteOut:
    return QuoteOut(
        symbol=symbol,
        company_name=symbol,
        current_price=0,
        previous_close=0,
        price_change_percent=0,
        volume=0,
        average_volume=0,
        volatility=0,
        market_cap=0,
        week_52_high=0,
        week_52_low=0,
        timestamp=datetime.now(UTC),
        source="none",
        data_status="UNAVAILABLE",
        market_state="UNKNOWN",
        explanation=message,
    )


def _quote_out(result, quote) -> QuoteOut:
    return QuoteOut(
        symbol=quote.symbol,
        company_name=quote.company_name,
        current_price=result.current_price,
        previous_close=quote.previous_close,
        previous_price=result.previous_price,
        price_change_percent=result.price_change_percent,
        since_last_check_percent=result.since_last_check_percent,
        volume=quote.volume,
        average_volume=quote.average_volume,
        volatility=quote.volatility,
        market_cap=quote.market_cap,
        week_52_high=quote.week_52_high,
        week_52_low=quote.week_52_low,
        timestamp=quote.timestamp,
        source=quote.source,
        data_status=result.data_status,  # type: ignore[arg-type]
        market_state=quote.market_state,
        first_seen=result.first_seen,
        significance_score=result.significance_score,
        severity=result.severity,  # type: ignore[arg-type]
        explanation=result.explanation,
        change_type=result.change_type,
        evidence=result.evidence,
    )


def _watched_symbols(lists: list[Watchlist]) -> list[str]:
    symbols: list[str] = []
    for wl in lists:
        for s in wl.stocks:
            if s.symbol not in symbols:
                symbols.append(s.symbol)
    return symbols


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Compare current snapshots to the acknowledged baseline. Does not advance last-seen."""
    lists = db.scalars(
        select(Watchlist).options(selectinload(Watchlist.stocks)).where(Watchlist.user_id == user.id)
    ).all()
    symbols = _watched_symbols(list(lists))
    prefs = db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
    high_only = bool(prefs.high_significance_only) if prefs else False
    emphasize = bool(prefs.unusual_volume_emphasis) if prefs else True

    last_state = db.scalars(
        select(UserStockState)
        .where(UserStockState.user_id == user.id)
        .order_by(UserStockState.last_seen_at.desc())
    ).first()

    market_service.prefetch(db, symbols)
    states = {}
    if symbols:
        for row in db.scalars(
            select(UserStockState).where(
                UserStockState.user_id == user.id, UserStockState.symbol.in_(symbols)
            )
        ).all():
            states[row.symbol] = row
    snaps = latest_snapshots_map(db, symbols)

    items: list[QuoteOut] = []
    unavailable: list[QuoteOut] = []
    first_time = last_state is None and bool(symbols)

    for symbol in symbols:
        try:
            quote, snap = market_service.get_quote(db, symbol)
            if not quote:
                unavailable.append(_unavailable(symbol, "Market data is unavailable for this symbol."))
                continue
            sid = snap.id if snap else (snaps.get(symbol).id if snaps.get(symbol) else None)
            result = compare_and_record(
                db,
                user.id,
                quote,
                sid,
                commit_last_seen=False,
                persist_history=True,
                sensitivity=user.sensitivity,
                lookback_mode=user.lookback_mode,
                emphasize_volume=emphasize,
                state=states.get(symbol),
            )
            q = _quote_out(result, quote)
            if result.data_status == "UNAVAILABLE":
                unavailable.append(q)
            else:
                items.append(q)
                record_notification(db, user.id, result)
        except Exception:  # noqa: BLE001
            unavailable.append(
                _unavailable(
                    symbol,
                    "This symbol failed independently and did not block the rest of the dashboard.",
                )
            )

    db.commit()
    items.sort(key=lambda x: (SEVERITY_RANK.get(x.severity, 9), -x.significance_score))
    needs = [i for i in items if i.severity == "HIGH" and not i.first_seen]
    meaningful = [i for i in items if i.severity in {"MEANINGFUL", "NOTABLE"} and not i.first_seen]
    if high_only:
        stable = [i for i in items if i not in needs]
        meaningful = []
    else:
        stable = [i for i in items if i.severity == "STABLE" or i.first_seen]
    statuses = [i.data_status for i in items]
    overall = "UNAVAILABLE" if not items and unavailable else "LIVE"
    if any(s == "STALE" for s in statuses):
        overall = "STALE"
    elif any(s == "DELAYED" for s in statuses):
        overall = "DELAYED"
    elif any(s == "LIVE" for s in statuses):
        overall = "LIVE"
    market_state = items[0].market_state if items else "CLOSED"

    return DashboardOut(
        greeting=f"{_hour_greeting()}, {user.name.split()[0]}",
        last_checked_at=last_state.last_seen_at if last_state else None,
        stocks_tracked=len(symbols),
        watchlist_count=len(lists),
        meaningful_changes=len(meaningful),
        needs_attention=len(needs),
        stable_count=len(stable),
        market_state=market_state,
        data_status=overall,  # type: ignore[arg-type]
        needs_attention_items=needs,
        meaningful_items=meaningful,
        stable_items=stable,
        unavailable_items=unavailable,
        first_time=first_time or (all(i.first_seen for i in items) and bool(items)),
        baseline_advances_on="acknowledge",
    )


@router.post("/dashboard/acknowledge", response_model=AcknowledgeOut)
def acknowledge(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lists = db.scalars(
        select(Watchlist).options(selectinload(Watchlist.stocks)).where(Watchlist.user_id == user.id)
    ).all()
    symbols = _watched_symbols(list(lists))
    market_service.prefetch(db, symbols)
    now = datetime.now(UTC)
    done: list[str] = []
    for symbol in symbols:
        quote, snap = market_service.get_quote(db, symbol)
        if not quote:
            continue
        acknowledge_quote(db, user.id, quote, snap.id if snap else None)
        done.append(symbol)
    db.commit()
    return AcknowledgeOut(
        acknowledged_at=now,
        symbols=done,
        message="Baseline updated. Later visits compare against this check until you acknowledge again.",
    )
