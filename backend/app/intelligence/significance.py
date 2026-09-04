from __future__ import annotations

WEIGHTS = {
    "price_abnormality": 0.40,
    "volume_anomaly": 0.25,
    "volatility_change": 0.15,
    "event_impact": 0.10,
    "user_relevance": 0.10,
}


def classify(score: float) -> str:
    if score >= 80:
        return "HIGH"
    if score >= 60:
        return "MEANINGFUL"
    if score >= 30:
        return "NOTABLE"
    return "STABLE"


def _clamp(value: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, value))


def price_abnormality(pct_change: float, daily_volatility: float) -> float:
    vol = max(daily_volatility, 0.005)
    z = abs(pct_change / 100.0) / vol
    return _clamp(z / 3.5 * 100)


def volume_anomaly(volume: float, average_volume: float) -> float:
    if average_volume <= 0:
        return 0
    ratio = volume / average_volume
    return _clamp((ratio - 1.0) / 1.5 * 100)


def volatility_component(daily_volatility: float, baseline: float = 0.018) -> float:
    if daily_volatility <= baseline:
        return 0
    return _clamp((daily_volatility - baseline) / 0.03 * 100)


def event_impact(volume_score: float, price_score: float) -> float:
    if volume_score > 60 and price_score > 50:
        return 80
    if volume_score > 40 or price_score > 70:
        return 45
    return 10


def user_relevance(in_primary_watchlist: bool, prior_attention: bool) -> float:
    score = 35
    if in_primary_watchlist:
        score += 35
    if prior_attention:
        score += 20
    return _clamp(score)


def significance_score(
    pct_change: float,
    daily_volatility: float,
    volume: float,
    average_volume: float,
    in_primary_watchlist: bool = True,
    prior_attention: bool = False,
) -> dict:
    p = price_abnormality(pct_change, daily_volatility)
    v = volume_anomaly(volume, average_volume)
    volc = volatility_component(daily_volatility)
    ev = event_impact(v, p)
    rel = user_relevance(in_primary_watchlist, prior_attention)
    total = (
        WEIGHTS["price_abnormality"] * p
        + WEIGHTS["volume_anomaly"] * v
        + WEIGHTS["volatility_change"] * volc
        + WEIGHTS["event_impact"] * ev
        + WEIGHTS["user_relevance"] * rel
    )
    score = round(_clamp(total), 1)
    return {
        "score": score,
        "severity": classify(score),
        "components": {
            "price_abnormality": round(p, 1),
            "volume_anomaly": round(v, 1),
            "volatility_change": round(volc, 1),
            "event_impact": round(ev, 1),
            "user_relevance": round(rel, 1),
        },
    }
