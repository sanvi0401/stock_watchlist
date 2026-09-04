"""Significance: is this move unusual *for this stock*?

Raw percent is a poor signal: 2% is a quiet day for TSLA and a big one for
COST. So the move is measured in units of the stock's own typical daily move
(z = |pct| / daily volatility), and volume is allowed to corroborate a move
but never to create one on its own: a flat price on heavy volume is not
"something changed since you looked".

    price     = z / 2.5           (2.5 typical-day moves = 100)
    volume    = (ratio - 1) / 1.5 (2.5x average volume = 100)
    score     = 0.8 * price + 0.2 * volume * min(1, z)

So a 1-sigma move is NOTABLE, 2-sigma is MEANINGFUL, 2.5-sigma or a 2-sigma
move on heavy volume is HIGH (balanced sensitivity).

Sensitivity scales the score and shifts the bands so a user can decide how
noisy they want the Overview to be.
"""

from __future__ import annotations

SENSITIVITY_SCALE = {"conservative": 0.82, "balanced": 1.0, "sensitive": 1.2}
SENSITIVITY_BANDS = {  # (HIGH, MEANINGFUL, NOTABLE) floors
    "conservative": (88.0, 70.0, 42.0),
    "balanced": (80.0, 60.0, 30.0),
    "sensitive": (70.0, 48.0, 18.0),
}
MIN_VOLATILITY = 0.005


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


def sigma(pct_change: float, daily_volatility: float) -> float:
    """How many typical daily moves the change represents."""
    return abs(pct_change / 100.0) / max(daily_volatility, MIN_VOLATILITY)


def price_abnormality(pct_change: float, daily_volatility: float) -> float:
    return _clamp(sigma(pct_change, daily_volatility) / 2.5 * 100)


def volume_anomaly(volume: float, average_volume: float) -> float:
    if average_volume <= 0:
        return 0.0
    return _clamp((volume / average_volume - 1.0) / 1.5 * 100)


def significance_score(
    pct_change: float,
    daily_volatility: float,
    volume: float,
    average_volume: float,
    sensitivity: str = "balanced",
) -> dict:
    z = sigma(pct_change, daily_volatility)
    p = price_abnormality(pct_change, daily_volatility)
    v = volume_anomaly(volume, average_volume)
    corroboration = v * min(1.0, z)
    total = 0.8 * p + 0.2 * corroboration
    score = round(_clamp(total * SENSITIVITY_SCALE.get(sensitivity, 1.0)), 1)
    return {
        "score": score,
        "severity": classify(score, sensitivity),
        "sigma": round(z, 2),
        "components": {
            "price_abnormality": round(p, 1),
            "volume_anomaly": round(v, 1),
            "volume_corroboration": round(corroboration, 1),
        },
    }
