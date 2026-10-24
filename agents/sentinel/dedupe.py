"""Merge duplicate events from different sources and score confidence. Owner: D2."""

from __future__ import annotations

from shared.geo import distance_km
from shared.models import Event

MERGE_DISTANCE_KM = 200
SEVERITY_RANK = {"Green": 0, "Orange": 1, "Red": 2}
SEVERITY_BONUS = {"Green": 0.0, "Orange": 0.1, "Red": 0.2}
EXTRA_SOURCE_BONUS = 0.15
MAX_CONFIDENCE = 0.95


def _merge(a: Event, b: Event) -> Event:
    primary, other = (a, b) if a.confidence >= b.confidence else (b, a)
    sources = list(dict.fromkeys([*primary.sources, *other.sources]))
    severity = max(primary.severity, other.severity, key=lambda s: SEVERITY_RANK.get(s, 0))
    confidence = min(
        MAX_CONFIDENCE,
        max(primary.confidence, other.confidence)
        + EXTRA_SOURCE_BONUS * (len(sources) - len(primary.sources))
        + SEVERITY_BONUS.get(severity, 0) - SEVERITY_BONUS.get(primary.severity, 0),
    )
    return primary.copy(
        update={
            "sources": sources,
            "severity": severity,
            "radius_km": max(primary.radius_km, other.radius_km),
            "confidence": round(confidence, 2),
        }
    )


def with_severity_bonus(event: Event) -> Event:
    """Single-source confidence: base + severity bonus, capped."""
    confidence = min(MAX_CONFIDENCE, event.confidence + SEVERITY_BONUS.get(event.severity, 0))
    return event.copy(update={"confidence": round(confidence, 2)})


def dedupe(events: list[Event]) -> list[Event]:
    """Merge same-type events whose centres are within 200 km. Sorted by confidence."""
    merged: list[Event] = []
    for event in events:
        for i, existing in enumerate(merged):
            if (
                existing.type == event.type
                and distance_km(existing.center, event.center) <= MERGE_DISTANCE_KM
            ):
                merged[i] = _merge(existing, event)
                break
        else:
            merged.append(event)
    return sorted(merged, key=lambda e: e.confidence, reverse=True)
