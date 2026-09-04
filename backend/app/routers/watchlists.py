from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.intelligence.last_seen import compare_and_record, load_states, start_state
from app.market.mock import UNIVERSE
from app.market.service import market_service
from app.models import User, UserStockState, Watchlist, WatchlistStock
from app.schemas import AddStockRequest, WatchlistCreate, WatchlistOut, WatchlistStockOut, WatchlistUpdate
from app.serializers import quote_out
from app.symbols import resolve_to_symbol

router = APIRouter(prefix="/watchlists", tags=["watchlists"])

_NOT_FOUND = AppError(404, "not_found", "Watchlist not found.")
_UNRESOLVED = AppError(
    404, "invalid_stock", "We couldn't find that company or ticker. Try a name like Google or a symbol like GOOGL."
)


def _seed_baseline(db: Session, user_id: int, symbol: str, states: dict[str, UserStockState]) -> None:
    """Adding a symbol is the first time the user 'saw' it: that price is the baseline.

    With the mock provider a 14-hour-old demo baseline is used instead so a
    fresh install has something to show on the very first Overview. Live
    providers never fabricate history.
    """
    if symbol in states:
        return
    quote, snap = market_service.get_quote(db, symbol)
    if not quote or quote.data_status == "UNAVAILABLE":
        return
    now = datetime.now(UTC)
    demo = UNIVERSE.get(symbol, {}).get("last_seen_demo") if settings.market_data_provider == "mock" else None
    if demo is not None:
        state = UserStockState(
            user_id=user_id,
            symbol=symbol,
            baseline_at=now - timedelta(hours=14),
            baseline_price=float(demo),
            last_seen_at=now - timedelta(hours=14),
            last_seen_price=float(demo),
            reference_snapshot_id=snap.id if snap else None,
        )
        db.add(state)
        states[symbol] = state
        return
    states[symbol] = start_state(db, user_id, symbol, quote.price, snap.id if snap else None, now)


def serialize_watchlist(db: Session, user: User, wl: Watchlist, with_quotes: bool = False) -> WatchlistOut:
    stocks: list[WatchlistStockOut] = []
    attention = meaningful = stable = unavailable = 0
    if with_quotes:
        symbols = [row.symbol for row in wl.stocks]
        market_service.prefetch(db, symbols)
        states = load_states(db, user.id, symbols)
        for row in wl.stocks:
            quote, snap = market_service.get_quote(db, row.symbol)
            if not quote:
                unavailable += 1
                stocks.append(WatchlistStockOut(symbol=row.symbol, added_at=row.added_at, quote=None))
                continue
            result = compare_and_record(
                db,
                user.id,
                quote,
                snap.id if snap else None,
                commit_last_seen=False,
                states=states,
                sensitivity=user.sensitivity,
                lookback_mode=user.lookback_mode,
            )
            stocks.append(WatchlistStockOut(symbol=row.symbol, added_at=row.added_at, quote=quote_out(result, quote)))
            if result.data_status == "UNAVAILABLE":
                unavailable += 1
            elif result.severity == "HIGH":
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
        unavailable_count=unavailable,
    )


def _load(db: Session, user: User, watchlist_id: int) -> Watchlist:
    wl = db.scalar(
        select(Watchlist)
        .options(selectinload(Watchlist.stocks))
        .where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id)
    )
    if not wl:
        raise _NOT_FOUND
    return wl


@router.get("", response_model=list[WatchlistOut])
def list_watchlists(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Watchlist)
        .options(selectinload(Watchlist.stocks))
        .where(Watchlist.user_id == user.id)
        .order_by(Watchlist.created_at)
    ).all()
    return [serialize_watchlist(db, user, wl, with_quotes=True) for wl in rows]


@router.post("", response_model=WatchlistOut, status_code=201)
def create_watchlist(body: WatchlistCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wl = Watchlist(user_id=user.id, name=body.name.strip(), category=body.category.strip() or "General")
    db.add(wl)
    db.flush()
    resolved: list[str] = []
    for raw in body.symbols[: settings.max_symbols_per_watchlist]:
        symbol = resolve_to_symbol(db, raw)
        if symbol and symbol not in resolved:
            resolved.append(symbol)
            db.add(WatchlistStock(watchlist_id=wl.id, symbol=symbol))
    market_service.prefetch(db, resolved)
    states = load_states(db, user.id, resolved)
    for symbol in resolved:
        _seed_baseline(db, user.id, symbol, states)
    db.commit()
    return serialize_watchlist(db, user, _load(db, user, wl.id), with_quotes=True)


@router.get("/{watchlist_id}", response_model=WatchlistOut)
def get_watchlist(watchlist_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize_watchlist(db, user, _load(db, user, watchlist_id), with_quotes=True)


@router.patch("/{watchlist_id}", response_model=WatchlistOut)
def update_watchlist(
    watchlist_id: int, body: WatchlistUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    wl = _load(db, user, watchlist_id)
    if body.name is not None:
        wl.name = body.name.strip()
    if body.category is not None:
        wl.category = body.category.strip() or "General"
    db.commit()
    return serialize_watchlist(db, user, _load(db, user, wl.id), with_quotes=True)


@router.delete("/{watchlist_id}", status_code=204)
def delete_watchlist(watchlist_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wl = _load(db, user, watchlist_id)
    db.delete(wl)
    db.commit()
    return None


@router.post("/{watchlist_id}/stocks", response_model=WatchlistOut)
def add_stock(
    watchlist_id: int, body: AddStockRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    wl = _load(db, user, watchlist_id)
    if len(wl.stocks) >= settings.max_symbols_per_watchlist:
        raise AppError(
            400,
            "watchlist_full",
            f"A watchlist holds up to {settings.max_symbols_per_watchlist} symbols. Create another list for more.",
        )
    symbol = resolve_to_symbol(db, body.symbol)
    if not symbol:
        raise _UNRESOLVED
    quote, _snap = market_service.get_quote(db, symbol)
    if not quote:
        raise _UNRESOLVED
    if any(s.symbol == symbol for s in wl.stocks):
        raise AppError(409, "duplicate_stock", f"{symbol} is already on this watchlist.")
    db.add(WatchlistStock(watchlist_id=wl.id, symbol=symbol))
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError:
        # Two adds of the same symbol raced; the unique constraint decides.
        raise AppError(409, "duplicate_stock", f"{symbol} is already on this watchlist.") from None
    _seed_baseline(db, user.id, symbol, load_states(db, user.id, [symbol]))
    db.commit()
    return serialize_watchlist(db, user, _load(db, user, wl.id), with_quotes=True)


@router.delete("/{watchlist_id}/stocks/{symbol}", response_model=WatchlistOut)
def remove_stock(
    watchlist_id: int, symbol: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    wl = _load(db, user, watchlist_id)
    symbol = symbol.upper()
    row = next((s for s in wl.stocks if s.symbol == symbol), None)
    if not row:
        raise AppError(404, "not_found", "That stock is not on this watchlist.")
    db.delete(row)
    db.commit()
    return serialize_watchlist(db, user, _load(db, user, wl.id), with_quotes=True)
