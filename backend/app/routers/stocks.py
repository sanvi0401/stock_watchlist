from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.intelligence.last_seen import compare_and_record
from app.market.service import market_service
from app.models import User, UserSettings, UserStockState
from app.schemas import HistoryPointOut, QuoteOut, SearchResult

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/search", response_model=list[SearchResult])
def search_stocks(
    q: str = Query(min_length=1),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    results = market_service.search(db, q)
    out: list[SearchResult] = []
    for quote in results:
        day = 0.0
        if quote.previous_close:
            day = (quote.price - quote.previous_close) / quote.previous_close * 100
        out.append(
            SearchResult(
                symbol=quote.symbol,
                company_name=quote.company_name,
                current_price=quote.price,
                price_change_percent=round(day, 2),
                data_status=quote.data_status,  # type: ignore[arg-type]
                market_state=quote.market_state,
            )
        )
    return out


@router.get("/{symbol}/history", response_model=list[HistoryPointOut])
def stock_history(
    symbol: str,
    range: str = Query("5d", pattern="^(1d|5d|1mo|1y)$"),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    points = market_service.history(db, symbol.upper(), range)
    return [HistoryPointOut(timestamp=p.timestamp, close=p.close, volume=p.volume) for p in points]


@router.get("/{symbol}", response_model=QuoteOut)
def stock_detail(
    symbol: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quote, snap = market_service.get_quote(db, symbol)
    if not quote:
        raise AppError(404, "stock_not_found", "We couldn't find that symbol.")
    prefs = db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
    emphasize = bool(prefs.unusual_volume_emphasis) if prefs else True
    state = db.scalar(
        select(UserStockState).where(UserStockState.user_id == user.id, UserStockState.symbol == quote.symbol)
    )
    result = compare_and_record(
        db,
        user.id,
        quote,
        snap.id if snap else None,
        commit_last_seen=False,
        persist_history=False,
        sensitivity=user.sensitivity,
        lookback_mode=user.lookback_mode,
        emphasize_volume=emphasize,
        state=state,
    )
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
