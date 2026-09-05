from __future__ import annotations

from sqlalchemy.orm import Session

from app.market.mock import UNIVERSE
from app.market.service import market_service
from app.symbol_names import NAME_TO_SYMBOL


def resolve_to_symbol(db: Session, query: str) -> str | None:
    raw = (query or "").strip()
    if not raw:
        return None
    upper = raw.upper()
    if upper in UNIVERSE:
        return upper
    hinted = NAME_TO_SYMBOL.get(raw.lower())
    if hinted:
        quote, _ = market_service.get_quote(db, hinted)
        if quote:
            return quote.symbol
        return hinted
    if upper.isalnum() and 1 <= len(upper) <= 6:
        quote, _ = market_service.get_quote(db, upper)
        if quote and quote.symbol == upper:
            return upper
    hits = market_service.search(db, raw)
    if not hits:
        return None
    needle = raw.lower()
    for hit in hits:
        if needle == hit.symbol.lower() or needle in hit.company_name.lower():
            return hit.symbol
    return hits[0].symbol
