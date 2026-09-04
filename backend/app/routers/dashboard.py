"""The Overview: the answer to "what changed since I last checked, and what matters now?"

Loading the dashboard is a *viewing*. Loading it again inside the visit window
is the same viewing (baseline unchanged). Loading it after the window starts a
new visit: baselines roll, changes are written to the ledger once.
"""

import logging
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import get_current_user
from app.intelligence.last_seen import checkpoint, compare_and_record, load_states
from app.market.freshness import as_utc, market_state
from app.market.service import market_service
from app.models import Notification, User, Watchlist
from app.schemas import CheckpointOut, DashboardOut, QuoteOut
from app.serializers import quote_out, unavailable_out

logger = logging.getLogger(__name__)
router = APIRouter(tags=["dashboard"])

SEVERITY_RANK = {"HIGH": 0, "MEANINGFUL": 1, "NOTABLE": 2, "STABLE": 3}


def _greeting(user: User) -> str:
    try:
        hour = datetime.now(ZoneInfo(user.timezone or "UTC")).hour
    except (ZoneInfoNotFoundError, ValueError):
        hour = datetime.now(UTC).hour
    word = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    return f"{word}, {user.name.split()[0] if user.name.strip() else 'there'}"


def _watched_symbols(db: Session, user: User) -> tuple[list[Watchlist], list[str]]:
    lists = db.scalars(
        select(Watchlist).options(selectinload(Watchlist.stocks)).where(Watchlist.user_id == user.id)
    ).all()
    symbols: list[str] = []
    for wl in lists:
        for s in wl.stocks:
            if s.symbol not in symbols:
                symbols.append(s.symbol)
    return list(lists), symbols


def _overall_status(items: list[QuoteOut]) -> str:
    statuses = {i.data_status for i in items}
    if not statuses:
        return "UNAVAILABLE"
    if "STALE" in statuses:
        return "STALE"
    if "DELAYED" in statuses:
        return "DELAYED"
    return "LIVE"


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lists, symbols = _watched_symbols(db, user)
    now = datetime.now(UTC)
    market_service.prefetch(db, symbols)
    states = load_states(db, user.id, symbols)
    had_state = bool(states)

    items: list[QuoteOut] = []
    unavailable: list[QuoteOut] = []
    new_visit = False
    baseline_at: datetime | None = None
    for symbol in symbols:
        try:
            quote, snap = market_service.get_quote(db, symbol)
            if not quote:
                unavailable.append(unavailable_out(symbol, "Market data is unavailable for this symbol."))
                continue
            result = compare_and_record(
                db,
                user.id,
                quote,
                snap.id if snap else None,
                commit_last_seen=True,
                states=states,
                sensitivity=user.sensitivity,
                lookback_mode=user.lookback_mode,
                now=now,
            )
            q = quote_out(result, quote)
            if result.data_status == "UNAVAILABLE":
                unavailable.append(q)
                continue
            items.append(q)
            new_visit = new_visit or result.new_visit
            if result.baseline_at and (baseline_at is None or result.baseline_at > baseline_at):
                baseline_at = result.baseline_at
            if result.recorded_change and result.severity in {"HIGH", "MEANINGFUL"}:
                db.add(
                    Notification(
                        user_id=user.id,
                        title=f"{symbol} · {result.severity.title()}",
                        body=result.explanation,
                        kind="change",
                    )
                )
        except Exception:  # noqa: BLE001
            # One bad symbol must never take down the whole Overview.
            logger.exception("dashboard failed for %s", symbol)
            unavailable.append(unavailable_out(symbol, "This symbol could not be evaluated; the rest of the dashboard is unaffected."))
    db.commit()

    items.sort(key=lambda x: (SEVERITY_RANK.get(x.severity, 9), -x.significance_score))
    needs = [i for i in items if i.severity == "HIGH" and not i.first_seen]
    if user.high_significance_only:
        meaningful: list[QuoteOut] = []
        stable = [i for i in items if i not in needs]
    else:
        meaningful = [i for i in items if i.severity in {"MEANINGFUL", "NOTABLE"} and not i.first_seen]
        stable = [i for i in items if i.severity == "STABLE" or i.first_seen]

    last_seen_values = [as_utc(s.last_seen_at) for s in states.values() if s.last_seen_at]
    return DashboardOut(
        greeting=_greeting(user),
        baseline_at=baseline_at,
        last_checked_at=max(last_seen_values) if last_seen_values else None,
        stocks_tracked=len(symbols),
        watchlist_count=len(lists),
        meaningful_changes=len(meaningful),
        needs_attention=len(needs),
        stable_count=len(stable),
        market_state=market_state(now),
        data_status=_overall_status(items) if items else ("UNAVAILABLE" if symbols else "LIVE"),  # type: ignore[arg-type]
        needs_attention_items=needs,
        meaningful_items=meaningful,
        stable_items=stable,
        unavailable_items=unavailable,
        first_time=bool(symbols) and (not had_state or all(i.first_seen for i in items)),
        new_visit=new_visit,
    )


@router.post("/dashboard/checkpoint", response_model=CheckpointOut)
def mark_all_seen(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """'I'm caught up.' Every watched symbol's baseline becomes its current price."""
    _lists, symbols = _watched_symbols(db, user)
    market_service.prefetch(db, symbols)
    quotes = []
    for symbol in symbols:
        quote, snap = market_service.get_quote(db, symbol)
        if quote:
            quotes.append((quote, snap.id if snap else None))
    now = datetime.now(UTC)
    count = checkpoint(db, user.id, quotes, now)
    db.commit()
    return CheckpointOut(symbols=count, baseline_at=now)
