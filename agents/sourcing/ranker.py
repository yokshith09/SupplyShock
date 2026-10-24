"""Rank alternate suppliers for one material. Owner: D2.

score = 0.4 * price_score + 0.3 * lead_time_score + 0.2 * quality_rating + 0.1 * (1 - risk_score)
price_score and lead_time_score are min-max normalised within the candidates (lower is better,
1.0 when all candidates are equal).
"""

from __future__ import annotations

W_PRICE, W_LEAD, W_QUALITY, W_RISK = 0.4, 0.3, 0.2, 0.1
TOP_N = 3


def _lower_is_better(value: float, low: float, high: float) -> float:
    if high == low:
        return 1.0
    return (high - value) / (high - low)


def score(candidate: dict, candidates: list[dict]) -> float:
    prices = [c["price_inr"] for c in candidates]
    leads = [c["lead_time_days"] for c in candidates]
    value = (
        W_PRICE * _lower_is_better(candidate["price_inr"], min(prices), max(prices))
        + W_LEAD * _lower_is_better(candidate["lead_time_days"], min(leads), max(leads))
        + W_QUALITY * candidate["quality_rating"]
        + W_RISK * (1 - candidate["risk_score"])
    )
    return round(value, 2)


def rank(candidates: list[dict], top_n: int = TOP_N) -> list[tuple[dict, float]]:
    scored = [(c, score(c, candidates)) for c in candidates]
    scored.sort(key=lambda pair: (-pair[1], pair[0]["price_inr"], pair[0]["id"]))
    return scored[:top_n]
