from app.intelligence.last_seen import compare_and_record
from app.market.types import NormalizedQuote
from sqlalchemy.orm import Session


def detect_for_symbols(
    db: Session,
    user_id: int,
    quotes: list[tuple[NormalizedQuote, int | None]],
    commit_last_seen: bool = True,
):
    results = []
    for quote, snapshot_id in quotes:
        results.append(
            compare_and_record(
                db,
                user_id,
                quote,
                snapshot_id,
                commit_last_seen=commit_last_seen,
            )
        )
    return results
