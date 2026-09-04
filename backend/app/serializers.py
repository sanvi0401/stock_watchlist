"""Build API responses from a quote plus the user's comparison result."""

from __future__ import annotations

from datetime import UTC, datetime

from app.intelligence.last_seen import ChangeResult
from app.market.freshness import market_state
from app.market.types import NormalizedQuote
from app.schemas import QuoteOut


def quote_out(result: ChangeResult, quote: NormalizedQuote) -> QuoteOut:
    return QuoteOut(
        symbol=quote.symbol,
        company_name=quote.company_name or quote.symbol,
        current_price=result.current_price,
        previous_close=quote.previous_close,
        previous_price=result.previous_price,
        baseline_at=result.baseline_at,
        price_change_percent=result.price_change_percent,
        since_last_check_percent=result.since_last_check_percent,
        volume=quote.volume,
        average_volume=quote.average_volume,
        volatility=quote.volatility,
        market_cap=quote.market_cap,
        week_52_high=quote.week_52_high,
        week_52_low=quote.week_52_low,
        sparkline=[round(float(x), 4) for x in (quote.sparkline or [])],
        currency=quote.currency,
        exchange=quote.exchange,
        exchange_name=quote.exchange_name,
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


def unavailable_out(symbol: str, explanation: str) -> QuoteOut:
    from app.market.freshness import exchange_for

    info = exchange_for(None, symbol)
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
        currency=info.currency,
        exchange=info.code,
        exchange_name=info.name,
        data_status="UNAVAILABLE",
        market_state=market_state(exchange=info.code),
        change_type="data_unavailable",
        explanation=explanation,
    )
