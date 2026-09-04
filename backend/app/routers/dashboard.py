from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import get_current_user
from app.intelligence.last_seen import compare_and_record
from app.market.service import market_service
from app.models import Notification, User, UserStockState, Watchlist
from app.schemas import DashboardOut, QuoteOut

router = APIRouter(tags=["dashboard"])

SEVERITY_RANK = {"HIGH": 0, "MEANINGFUL": 1, "NOTABLE": 2, "STABLE": 3, "UNAVAILABLE": 4}


def _hour_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lists = db.scalars(
        select(Watchlist).options(selectinload(Watchlist.stocks)).where(Watchlist.user_id == user.id)
    ).all()
    symbols: list[str] = []
    for wl in lists:
        for s in wl.stocks:
            if s.symbol not in symbols:
                symbols.append(s.symbol)

    last_state = db.scalars(
        select(UserStockState)
        .where(UserStockState.user_id == user.id)
        .order_by(UserStockState.last_seen_at.desc())
    ).first()

    items: list[QuoteOut] = []
    unavailable: list[QuoteOut] = []
    first_time = last_state is None and bool(symbols)

    for symbol in symbols:
        try:
            quote, snap = market_service.get_quote(db, symbol)
            if not quote:
                unavailable.append(
                    QuoteOut(
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
                        timestamp=datetime.now(timezone.utc),
                        source="none",
                        data_status="UNAVAILABLE",
                        market_state="UNKNOWN",
                        explanation="Market data is unavailable for this symbol.",
                    )
                )
                continue
            result = compare_and_record(
                db, user.id, quote, snap.id if snap else None, commit_last_seen=True
            )
            q = QuoteOut(
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
            if result.data_status == "UNAVAILABLE":
                unavailable.append(q)
            else:
                items.append(q)
                if result.severity in {"HIGH", "MEANINGFUL"} and not result.first_seen:
                    db.add(
                        Notification(
                            user_id=user.id,
                            title=f"{symbol} · {result.severity.title()}",
                            body=result.explanation,
                            kind="change",
                        )
                    )
        except Exception:  # noqa: BLE001
            unavailable.append(
                QuoteOut(
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
                    timestamp=datetime.now(timezone.utc),
                    source="none",
                    data_status="UNAVAILABLE",
                    market_state="UNKNOWN",
                    explanation="This symbol failed independently and did not block the rest of the dashboard.",
                )
            )

    db.commit()
    items.sort(key=lambda x: (SEVERITY_RANK.get(x.severity, 9), -x.significance_score))
    needs = [i for i in items if i.severity == "HIGH" and not i.first_seen]
    meaningful = [i for i in items if i.severity in {"MEANINGFUL", "NOTABLE"} and not i.first_seen]
    stable = [i for i in items if i.severity == "STABLE" or i.first_seen]
    statuses = [i.data_status for i in items]
    overall = "LIVE"
    if any(s == "STALE" for s in statuses):
        overall = "STALE"
    if any(s == "DELAYED" for s in statuses) and overall == "LIVE":
        overall = "DELAYED"
    market_state = items[0].market_state if items else "OPEN"

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
        first_time=first_time or all(i.first_seen for i in items) and bool(items),
    )
