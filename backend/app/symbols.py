from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.market.mock import UNIVERSE
from app.market.service import market_service
from app.symbol_names import NAME_TO_SYMBOL

# Yahoo-style symbols: AAPL, RELIANCE.NS, VOD.L, 7203.T, BRK-B, ^NSEI
_SYMBOL = re.compile(r"^[A-Z0-9^][A-Z0-9.\-=&]{0,19}$")


def looks_like_symbol(text: str) -> bool:
    return bool(_SYMBOL.match(text)) and " " not in text


def resolve_to_symbol(db: Session, query: str) -> str | None:
    """Turn what a person typed ("reliance", "TCS.NS", "google") into one tradable symbol."""
    raw = (query or "").strip()
    if not raw:
        return None
    upper = raw.upper()
    if upper in UNIVERSE:
        return upper
    hinted = NAME_TO_SYMBOL.get(raw.lower())
    if hinted:
        quote, _ = market_service.get_quote(db, hinted)
        return quote.symbol if quote else hinted
    if looks_like_symbol(upper):
        quote, _ = market_service.get_quote(db, upper)
        if quote and quote.symbol == upper:
            return upper
    hits = market_service.search(db, raw)
    if not hits:
        return None
    needle = raw.lower()
    for hit in hits:
        if needle == hit.symbol.lower() or hit.company_name.lower().startswith(needle):
            return hit.symbol
    return hits[0].symbol
