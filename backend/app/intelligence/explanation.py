"""Plain-language explanation of a change, with the evidence used to reach it."""

from __future__ import annotations


def explain_change(
    symbol: str,
    pct_change: float,
    volume_ratio: float,
    volatility: float,
    severity: str,
    first_seen: bool,
    data_status: str,
    *,
    sigma: float = 0.0,
    baseline_label: str = "since you last checked",
) -> tuple[str, str, list[str]]:
    if first_seen:
        return (
            "initialized",
            f"{symbol} was added to your watchlist. This price is your baseline; no change is claimed until you come back.",
            ["First observation recorded", f"Typical daily move ≈ {volatility:.1%}"],
        )
    if data_status == "UNAVAILABLE":
        return (
            "data_unavailable",
            f"Quotes for {symbol} are unavailable right now. Your last valid price was kept and is not treated as current.",
            ["Provider returned nothing valid", "Previous state preserved"],
        )

    direction = "up" if pct_change >= 0 else "down"
    vol_txt = f"{volume_ratio:.1f}× its usual volume" if volume_ratio else "typical volume"
    evidence = [
        f"Move {baseline_label}: {pct_change:+.2f}%",
        f"That is {sigma:.1f}× this name's typical daily move ({volatility:.1%})",
        f"Volume: {vol_txt}",
        f"Feed: {data_status}",
    ]

    if severity == "HIGH":
        change_type = "high_significance_move"
        text = (
            f"{symbol} is {direction} {abs(pct_change):.1f}% {baseline_label}, "
            f"about {sigma:.1f}× its normal daily range, on {vol_txt}. This is unusual for {symbol}."
        )
    elif severity == "MEANINGFUL":
        change_type = "meaningful_move"
        text = (
            f"{symbol} moved {direction} {abs(pct_change):.1f}% {baseline_label}. "
            f"Larger than its usual day ({sigma:.1f}× typical) with {vol_txt}."
        )
    elif severity == "NOTABLE":
        change_type = "notable_move"
        text = (
            f"{symbol} is {direction} {abs(pct_change):.1f}% {baseline_label}. "
            "Worth a glance, but inside its normal range."
        )
    else:
        change_type = "stable"
        text = f"{symbol} is within its normal range {baseline_label} ({pct_change:+.2f}%)."
        if volume_ratio >= 1.5:
            text += f" Volume is elevated ({volume_ratio:.1f}× usual) but the price has not moved with it."
        else:
            text += " Nothing unusual in volume."
    if data_status == "STALE":
        text += " The quote is stale, so treat the size of this move with caution."
    elif data_status == "DELAYED":
        text += " Quote is delayed, not live."
    return change_type, text, evidence
