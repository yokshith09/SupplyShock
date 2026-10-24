"""Stock cover, disruption length and severity rules. Owner: D2. See docs/TRD.md §10."""

from __future__ import annotations

import math
import os
from datetime import date, timedelta

# Expected disruption length (days) by event type and alert level.
DISRUPTION_DAYS = {
    "cyclone": {"Green": 7, "Orange": 14, "Red": 21},
    "flood": {"Green": 5, "Orange": 10, "Red": 15},
    "earthquake": {"Green": 10, "Orange": 21, "Red": 30},
    "wildfire": {"Green": 5, "Orange": 7, "Red": 10},
    "strike": {"Green": 5, "Orange": 7, "Red": 14},
    "port_closure": {"Green": 5, "Orange": 10, "Red": 14},
    "fire": {"Green": 7, "Orange": 14, "Red": 21},
    "sanction": {"Green": 30, "Orange": 60, "Red": 90},
}
DEFAULT_DISRUPTION_DAYS = 7

SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MED": 2, "LOW": 3}


def today() -> date:
    pinned = os.getenv("SEED_TODAY")
    return date.fromisoformat(pinned) if pinned else date.today()


def disruption_days(event_type: str, alert_level: str) -> int:
    by_level = DISRUPTION_DAYS.get(event_type.lower())
    if not by_level:
        return DEFAULT_DISRUPTION_DAYS
    return by_level.get(alert_level, by_level.get("Orange", DEFAULT_DISRUPTION_DAYS))


def cover_days(on_hand_qty: float, daily_consumption: float) -> float:
    if daily_consumption <= 0:
        return math.inf
    return round(on_hand_qty / daily_consumption, 1)


def stockout_date(cover: float, start: date) -> str | None:
    if math.isinf(cover):
        return None
    return (start + timedelta(days=math.floor(cover))).isoformat()


def severity(cover: float, disruption: int, alt_lead_days: int | None) -> str:
    """CRITICAL: runs out before the fastest alternate could deliver (or before the disruption
    ends if there is no alternate). HIGH: runs out during the disruption. MED: within 2x."""
    if alt_lead_days is not None and cover < alt_lead_days:
        return "CRITICAL"
    if alt_lead_days is None and cover < disruption:
        return "CRITICAL"
    if cover < disruption:
        return "HIGH"
    if cover < 2 * disruption:
        return "MED"
    return "LOW"
