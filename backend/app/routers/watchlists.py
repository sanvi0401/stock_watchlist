from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.intelligence.last_seen import compare_and_record
from app.market.mock import UNIVERSE
from app.market.service import market_service
from app.models import User, UserSettings, UserStockState, Watchlist, WatchlistStock
from app.schemas import AddStockRequest, QuoteOut, WatchlistCreate, WatchlistOut, WatchlistStockOut, WatchlistUpdate
from app.symbols import resolve_to_symbol

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


def _quote_out(result, quote, company: str) -> QuoteOut:
    return QuoteOut(
        symbol=quote.symbol,
        company_name=company or quote.company_name,
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


def _seed_baseline(db: Session, user_id: int, symbol: str) -> None:
    """Demo-only: mock provider may seed an old last-seen so the first screen shows a delta.

    Production / Yahoo providers never invent a prior observation.
    """
    exists = db.query(UserStockState).filter_by(user_id=user_id, symbol=symbol).one_or_none()
    if exists:
        return
    if settings.market_data_provider != "mock":
        return
    demo = UNIVERSE.get(symbol, {}).get("last_seen_demo")
    if demo is None:
        return
    db.add(
        UserStockState(
            user_id=user_id,
            symbol=symbol,
            last_seen_at=datetime.now(UTC) - timedelta(hours=14),
            last_seen_price=float(demo),
        )
    )


def serialize_watchlist(db: Session, user: User, wl: Watchlist, with_quotes: bool = False) -> WatchlistOut:
    stocks = []
    attention = meaningful = stable = 0
    if with_quotes:
        symbols = [row.symbol for row in wl.stocks]
        market_service.prefetch(db, symbols)
        prefs = db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
        emphasize = bool(prefs.unusual_volume_emphasis) if prefs else True
        states = {}
        if symbols:
            for st in db.scalars(
                select(UserStockState).where(
                    UserStockState.user_id == user.id, UserStockState.symbol.in_(symbols)
                )
            ).all():
                states[st.symbol] = st
        for row in wl.stocks:
            quote, snap = market_service.get_quote(db, row.symbol)
            if not quote:
                stocks.append(WatchlistStockOut(symbol=row.symbol, added_at=row.added_at, quote=None))
                continue
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
                state=states.get(row.symbol),
            )
            qout = _quote_out(result, quote, quote.company_name)
            stocks.append(WatchlistStockOut(symbol=row.symbol, added_at=row.added_at, quote=qout))
            if result.severity == "HIGH":
                attention += 1
            elif result.severity in {"MEANINGFUL", "NOTABLE"}:
                meaningful += 1
            else:
                stable += 1
    return WatchlistOut(
        id=wl.id,
        name=wl.name,
        category=wl.category,
        created_at=wl.created_at,
        stock_count=len(wl.stocks),
        stocks=stocks,
        attention_count=attention,
        meaningful_count=meaningful,
        stable_count=stable,
    )


@router.get("", response_model=list[WatchlistOut])
def list_watchlists(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Watchlist).options(selectinload(Watchlist.stocks)).where(Watchlist.user_id == user.id)
    ).all()
    return [serialize_watchlist(db, user, wl, with_quotes=True) for wl in rows]


@router.post("", response_model=WatchlistOut, status_code=201)
def create_watchlist(
    body: WatchlistCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    wl = Watchlist(user_id=user.id, name=body.name.strip(), category=body.category)
    db.add(wl)
    db.flush()
    seen: set[str] = set()
    for raw in body.symbols:
        symbol = resolve_to_symbol(db, raw)
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        db.add(WatchlistStock(watchlist_id=wl.id, symbol=symbol))
    market_service.prefetch(db, list(seen))
    for symbol in seen:
        _seed_baseline(db, user.id, symbol)
    db.commit()
    db.refresh(wl)
    wl = db.scalar(
        select(Watchlist).options(selectinload(Watchlist.stocks)).where(Watchlist.id == wl.id)
    )
    return serialize_watchlist(db, user, wl, with_quotes=True)


@router.get("/{watchlist_id}", response_model=WatchlistOut)
def get_watchlist(
    watchlist_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    wl = db.scalar(
        select(Watchlist)
        .options(selectinload(Watchlist.stocks))
        .where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id)
    )
    if not wl:
        raise AppError(404, "not_found", "Watchlist not found.")
    return serialize_watchlist(db, user, wl, with_quotes=True)


@router.patch("/{watchlist_id}", response_model=WatchlistOut)
def update_watchlist(
    watchlist_id: int,
    body: WatchlistUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wl = db.scalar(select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id))
    if not wl:
        raise AppError(404, "not_found", "Watchlist not found.")
    if body.name is not None:
        wl.name = body.name.strip()
    if body.category is not None:
        wl.category = body.category
    db.commit()
    wl = db.scalar(
        select(Watchlist).options(selectinload(Watchlist.stocks)).where(Watchlist.id == wl.id)
    )
    return serialize_watchlist(db, user, wl, with_quotes=True)


@router.delete("/{watchlist_id}", status_code=204)
def delete_watchlist(
    watchlist_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    wl = db.scalar(select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id))
    if not wl:
        raise AppError(404, "not_found", "Watchlist not found.")
    db.delete(wl)
    db.commit()
    return None


@router.post("/{watchlist_id}/stocks", response_model=WatchlistOut)
def add_stock(
    watchlist_id: int,
    body: AddStockRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wl = db.scalar(
        select(Watchlist)
        .options(selectinload(Watchlist.stocks))
        .where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id)
    )
    if not wl:
        raise AppError(404, "not_found", "Watchlist not found.")
    symbol = resolve_to_symbol(db, body.symbol)
    if not symbol:
        raise AppError(
            404,
            "invalid_stock",
            "We couldn't find that company or ticker. Try a name like Google or a symbol like GOOGL.",
        )
    quote, _snap = market_service.get_quote(db, symbol)
    if not quote:
        raise AppError(404, "invalid_stock", "We couldn't find that symbol.")
    if any(s.symbol == symbol for s in wl.stocks):
        raise AppError(409, "duplicate_stock", f"{symbol} is already on this watchlist.")
    db.add(WatchlistStock(watchlist_id=wl.id, symbol=symbol))
    _seed_baseline(db, user.id, symbol)
    db.commit()
    wl = db.scalar(
        select(Watchlist).options(selectinload(Watchlist.stocks)).where(Watchlist.id == wl.id)
    )
    return serialize_watchlist(db, user, wl, with_quotes=True)


@router.delete("/{watchlist_id}/stocks/{symbol}", response_model=WatchlistOut)
def remove_stock(
    watchlist_id: int,
    symbol: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wl = db.scalar(
        select(Watchlist)
        .options(selectinload(Watchlist.stocks))
        .where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id)
    )
    if not wl:
        raise AppError(404, "not_found", "Watchlist not found.")
    symbol = symbol.upper()
    row = next((s for s in wl.stocks if s.symbol == symbol), None)
    if not row:
        raise AppError(404, "not_found", "That stock is not on this watchlist.")
    db.delete(row)
    db.commit()
    wl = db.scalar(
        select(Watchlist).options(selectinload(Watchlist.stocks)).where(Watchlist.id == wl.id)
    )
    return serialize_watchlist(db, user, wl, with_quotes=True)
