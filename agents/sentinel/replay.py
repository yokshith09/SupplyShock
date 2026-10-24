"""Replay mode: serve a recorded past event with dates shifted to "today". Owner: D2.

Env: REPLAY_MODE=true to enable; SEED_TODAY=YYYY-MM-DD pins "today" (same as the seed).
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path

from shared.models import Event

REPLAY_DIR = Path(__file__).resolve().parents[2] / "data" / "replay_events"


def enabled() -> bool:
    return os.getenv("REPLAY_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}


def today() -> date:
    pinned = os.getenv("SEED_TODAY")
    return date.fromisoformat(pinned) if pinned else date.today()


def replay_events() -> list[Event]:
    events = []
    start = today()
    for path in sorted(REPLAY_DIR.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        duration = int(raw.get("duration_days", 7))
        events.append(
            Event(
                event_id=raw["event_id"],
                type=raw["type"],
                title=raw["title"],
                center=raw["center"],
                radius_km=raw["radius_km"],
                severity=raw["severity"],
                start=start.isoformat(),
                end=(start + timedelta(days=duration)).isoformat(),
                sources=raw["sources"],
                confidence=raw["confidence"],
            )
        )
    return events
