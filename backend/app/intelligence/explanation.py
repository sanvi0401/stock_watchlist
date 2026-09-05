def explain_change(
    symbol: str,
    pct_change: float,
    volume_ratio: float,
    volatility: float,
    severity: str,
    first_seen: bool,
    data_status: str,
    volatility_units: float | None = None,
    regime_label: str | None = None,
) -> tuple[str, str, list[str]]:
    if first_seen:
        return (
            "initialized",
            f"{symbol} has no acknowledged baseline yet. This price is shown for context; "
            "we will not claim a change until you mark this check as seen.",
            ["No prior acknowledgement", f"Recent daily volatility ≈ {volatility:.1%}"],
        )
    if data_status == "UNAVAILABLE":
        return (
            "data_unavailable",
            f"Quotes for {symbol} are unavailable. Your last acknowledged price was kept "
            "and is not treated as a live print.",
            ["Provider miss", "Acknowledged baseline preserved"],
        )

    direction = "increased" if pct_change >= 0 else "declined"
    vol_txt = f"{volume_ratio:.1f}× typical volume (session-scaled)" if volume_ratio else "typical volume"
    units_txt = f"{volatility_units:.1f}× its recent daily volatility" if volatility_units is not None else "its own recent volatility"
    evidence = [
        f"Move since last acknowledged check: {pct_change:+.2f}%",
        f"Volatility-standardized move: {units_txt}",
        f"Volume vs typical: {vol_txt}",
        f"Feed status: {data_status}",
    ]
    if regime_label and regime_label not in {"insufficient_history", "typical_regime"}:
        evidence.append(f"Short vs longer realized vol: {regime_label.replace('_', ' ')}")

    if severity == "HIGH":
        change_type = "high_significance_move"
        text = (
            f"{symbol} {direction} {abs(pct_change):.1f}% since you last acknowledged a check — "
            f"{units_txt}, with {vol_txt}."
        )
    elif severity == "MEANINGFUL":
        change_type = "meaningful_move"
        text = (
            f"{symbol} {direction} {abs(pct_change):.1f}% since your last acknowledged check. "
            f"Large relative to {units_txt} ({vol_txt})."
        )
    elif severity == "NOTABLE":
        change_type = "notable_move"
        text = (
            f"{symbol} {direction} {abs(pct_change):.1f}% since you last acknowledged a check. "
            "Worth a glance, still inside a broader normal band."
        )
    else:
        change_type = "stable"
        text = (
            f"{symbol} is within its normal band since you last acknowledged a check "
            f"({pct_change:+.2f}%)."
        )
    if data_status in {"STALE", "DELAYED"}:
        text += f" Quote is {data_status.lower()} — not a live print."
    return change_type, text, evidence
