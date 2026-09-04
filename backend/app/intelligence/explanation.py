def explain_change(
    symbol: str,
    pct_change: float,
    volume_ratio: float,
    volatility: float,
    severity: str,
    first_seen: bool,
    data_status: str,
) -> tuple[str, str, list[str]]:
    if first_seen:
        return (
            "initialized",
            f"{symbol} was added to your watchlist. We'll remember this price as your baseline — no change is claimed until you check again.",
            ["First observation recorded", f"Baseline volatility {volatility:.1%} daily"],
        )
    if data_status == "UNAVAILABLE":
        return (
            "data_unavailable",
            f"Live quotes for {symbol} are unavailable. Your last valid observation was kept and is not treated as a live price.",
            ["Provider miss", "Previous valid state preserved"],
        )

    direction = "increased" if pct_change >= 0 else "declined"
    vol_txt = f"{volume_ratio:.1f}× average volume" if volume_ratio else "typical volume"
    evidence = [
        f"Move since last check: {pct_change:+.2f}%",
        f"Volume vs typical: {vol_txt}",
        f"Typical daily range ≈ {volatility:.1%}",
        f"Feed status: {data_status}",
    ]

    if severity == "HIGH":
        change_type = "high_significance_move"
        text = (
            f"{symbol} {direction} {abs(pct_change):.1f}% since you last checked, "
            f"which is well outside its typical daily range, with {vol_txt}."
        )
    elif severity == "MEANINGFUL":
        change_type = "meaningful_move"
        text = (
            f"{symbol} {direction} {abs(pct_change):.1f}% since your last check. "
            f"The move is large relative to its usual volatility ({vol_txt})."
        )
    elif severity == "NOTABLE":
        change_type = "notable_move"
        text = (
            f"{symbol} {direction} {abs(pct_change):.1f}% since you last looked. "
            "Worth a glance, but still within a broader normal band."
        )
    else:
        change_type = "stable"
        text = (
            f"{symbol} is within its normal band since you last checked "
            f"({pct_change:+.2f}%). No unusual volume or volatility signal."
        )
    if data_status in {"STALE", "DELAYED"}:
        text += f" Quote is marked {data_status.lower()} — not live."
    return change_type, text, evidence
