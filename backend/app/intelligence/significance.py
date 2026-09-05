from __future__ import annotations

from app.market.calendar import session_elapsed_fraction

WEIGHTS = {
    "price_abnormality": 0.50,
    "volume_anomaly": 0.25,
    "volatility_regime": 0.25,
}

SENSITIVITY_SCALE = {
    "conservative": 0.82,
    "balanced": 1.0,
    "sensitive": 1.2,
}
SENSITIVITY_BANDS = {
    "conservative": (88.0, 70.0, 42.0),
    "balanced": (80.0, 60.0, 30.0),
    "sensitive": (70.0, 48.0, 18.0),
}


def classify(score: float, sensitivity: str = "balanced") -> str:
    high, meaningful, notable = SENSITIVITY_BANDS.get(sensitivity, SENSITIVITY_BANDS["balanced"])
    if score >= high:
        return "HIGH"
    if score >= meaningful:
        return "MEANINGFUL"
    if score >= notable:
        return "NOTABLE"
    return "STABLE"


def notable_floor(sensitivity: str = "balanced") -> float:
    return SENSITIVITY_BANDS.get(sensitivity, SENSITIVITY_BANDS["balanced"])[2]


def _clamp(value: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, value))


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return var ** 0.5


def volatility_units(pct_change: float, daily_returns: list[float] | None, fallback_vol: float) -> float:
    """Absolute return divided by the stock's own recent daily-return stdev.

    This is a volatility-standardized move, not a mean-adjusted z-score.
    """
    vol = _std(daily_returns) if daily_returns and len(daily_returns) >= 5 else max(fallback_vol, 0.005)
    vol = max(vol, 0.005)
    return abs(pct_change / 100.0) / vol


def price_abnormality(pct_change: float, daily_volatility: float, daily_returns: list[float] | None = None) -> float:
    units = volatility_units(pct_change, daily_returns, daily_volatility)
    return _clamp(units / 3.5 * 100)


def volume_anomaly(volume: float, average_volume: float, *, session_fraction: float | None = None) -> float:
    """Compare volume so far to a time-scaled typical full-day volume.

    Without true volume-by-time-of-day history this is conservative: early in
    the session we scale expected volume down and never claim high precision.
    """
    if average_volume <= 0 or volume <= 0:
        return 0
    frac = session_fraction if session_fraction is not None else session_elapsed_fraction()
    if frac < 0.12:
        return 0
    expected = average_volume * max(frac, 0.12)
    ratio = volume / expected
    # Dampen: 1.0× expected → 0, 2.5× → 100
    return _clamp((ratio - 1.0) / 1.5 * 100)


def volatility_regime(daily_returns: list[float] | None, fallback_vol: float) -> tuple[float, str]:
    """Short-window vs longer-window realized vol. Returns (score, label)."""
    rets = daily_returns or []
    if len(rets) < 10:
        return 0.0, "insufficient_history"
    short = _std(rets[-5:]) if len(rets) >= 5 else 0.0
    long = _std(rets[-30:] if len(rets) >= 30 else rets)
    if long < 0.004:
        long = max(fallback_vol, 0.004)
    if short <= 0:
        return 0.0, "stable_regime"
    ratio = short / long
    if ratio >= 1.6:
        return _clamp((ratio - 1.0) / 1.2 * 100), "elevated_short_vol"
    if ratio <= 0.7:
        return 0.0, "quiet_regime"
    return _clamp((ratio - 1.0) / 1.5 * 50), "typical_regime"


def significance_score(
    pct_change: float,
    daily_volatility: float,
    volume: float,
    average_volume: float,
    daily_returns: list[float] | None = None,
    sensitivity: str = "balanced",
    emphasize_volume: bool = True,
    session_fraction: float | None = None,
) -> dict:
    p = price_abnormality(pct_change, daily_volatility, daily_returns)
    v = volume_anomaly(volume, average_volume, session_fraction=session_fraction)
    if not emphasize_volume:
        v *= 0.35
    regime_score, regime_label = volatility_regime(daily_returns, daily_volatility)
    units = volatility_units(pct_change, daily_returns, daily_volatility)
    total = (
        WEIGHTS["price_abnormality"] * p
        + WEIGHTS["volume_anomaly"] * v
        + WEIGHTS["volatility_regime"] * regime_score
    )
    scale = SENSITIVITY_SCALE.get(sensitivity, 1.0)
    score = round(_clamp(total * scale), 1)
    return {
        "score": score,
        "severity": classify(score, sensitivity),
        "volatility_units": round(units, 2),
        "regime_label": regime_label,
        "components": {
            "price_abnormality": round(p, 1),
            "volume_anomaly": round(v, 1),
            "volatility_regime": round(regime_score, 1),
        },
    }
