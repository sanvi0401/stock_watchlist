from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.intelligence.last_seen import compare_and_record
from app.market.service import market_service
from app.models import User
from app.schemas import QuoteOut, SearchResult
from app.serializers import quote_out

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/search", response_model=list[SearchResult])
def search_stocks(
    q: str = Query(min_length=1, max_length=80),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    out: list[SearchResult] = []
    for quote in market_service.search(db, q):
        day = (quote.price - quote.previous_close) / quote.previous_close * 100 if quote.previous_close else 0.0
        out.append(
            SearchResult(
                symbol=quote.symbol,
                company_name=quote.company_name,
                current_price=quote.price,
                price_change_percent=round(day, 2),
                currency=quote.currency,
                exchange=quote.exchange,
                exchange_name=quote.exchange_name,
                data_status=quote.data_status,  # type: ignore[arg-type]
                market_state=quote.market_state,
            )
        )
    return out


@router.get("/{symbol}", response_model=QuoteOut)
def stock_detail(symbol: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Read-only: viewing one stock never moves the user's baseline. Only the Overview does."""
    quote, snap = market_service.get_quote(db, symbol)
    if not quote:
        raise AppError(404, "stock_not_found", "We couldn't find that symbol.")
    result = compare_and_record(
        db,
        user.id,
        quote,
        snap.id if snap else None,
        commit_last_seen=False,
        sensitivity=user.sensitivity,
        lookback_mode=user.lookback_mode,
    )
    db.commit()
    return quote_out(result, quote)
