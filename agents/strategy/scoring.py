"""Score options (TRD §11). Owner: D2.

score = 0.4 * risk_reduction + 0.3 * orders_saved_ratio - 0.2 * cost_ratio - 0.1 * time_ratio
  cost_ratio = cost_delta / revenue_at_risk   (capped at 1)
  time_ratio = time_to_effect / disruption    (capped at 1)
Ratios are used instead of min-max so one cheap option doesn't make every other look terrible.
"""

from __future__ import annotations

W_RISK, W_ORDERS, W_COST, W_TIME = 0.4, 0.3, 0.2, 0.1


def score(
    risk_reduction: float,
    orders_saved: int,
    orders_total: int,
    cost_delta_inr: float,
    revenue_at_risk_inr: float,
    time_to_effect_days: int,
    disruption_days: int,
) -> float:
    orders_ratio = orders_saved / orders_total if orders_total else 0.0
    cost_ratio = min(1.0, cost_delta_inr / revenue_at_risk_inr) if revenue_at_risk_inr else 1.0
    time_ratio = min(1.0, time_to_effect_days / disruption_days) if disruption_days else 0.0
    value = W_RISK * risk_reduction + W_ORDERS * orders_ratio - W_COST * cost_ratio - W_TIME * time_ratio
    return round(value, 3)
