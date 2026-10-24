"""Sentinel: detect disruption events near a location. Owner: D2.

    async def handle(req: EventQuery) -> EventResult

Sources: replay file (REPLAY_MODE=true), GDACS (live disasters), Open-Meteo (severe weather
forecast at the location). Never raises for source failures: returns degraded=True with notes.
Raises ServiceError(INVALID_INPUT) only when the location does not exist.
"""

from __future__ import annotations

import asyncio
import logging
import time

from agents.sentinel import gdacs, replay, weather
from agents.sentinel.dedupe import dedupe, with_severity_bonus
from agents.sentinel.geocode import GeocodeUnavailable, geocode, known_place
from shared.constants import ErrorCode
from shared.geo import distance_km
from shared.models import Event, EventQuery, EventResult, ServiceError

logger = logging.getLogger("supplyshock.sentinel")

NEARBY_KM = 500  # keep events whose impact zone edge is within this distance of the location
SOURCE_TIMEOUT_S = 12
CACHE_TTL_S = 15 * 60  # GDACS result is reused for 15 min
STALE_MAX_S = 6 * 60 * 60  # if GDACS is down/slow, fall back to a result up to 6 h old

# The GDACS feed is global, so one cache serves every location (filtered locally).
_gdacs_cache: dict[str, tuple[float, list[Event]]] = {}


def clear_cache() -> None:
    _gdacs_cache.clear()


async def refresh_gdacs() -> int:
    """Fetch GDACS into the cache. Call at agent start-up and on an interval (GDACS can take
    8-25 s to answer, so warming the cache keeps user requests fast).
    Returns the event count, or -1 if GDACS failed (never raises)."""
    today = replay.today()
    try:
        events = await gdacs.fetch_events(today, timeout_s=30)
    except gdacs.GDACSError as exc:
        logger.warning("gdacs warm-up failed: %r", exc)
        return -1
    _gdacs_cache[today.isoformat()] = (time.monotonic(), events)
    return len(events)


async def _gdacs_events() -> tuple[list[Event], str | None]:
    """(events, note). Raises if GDACS fails and there is no usable stale copy."""
    today = replay.today().isoformat()
    cached = _gdacs_cache.get(today)
    age = time.monotonic() - cached[0] if cached else None
    if cached and age < CACHE_TTL_S:
        return cached[1], None
    try:
        events = await asyncio.wait_for(gdacs.fetch_events(replay.today()), SOURCE_TIMEOUT_S)
    except Exception:
        if cached and age < STALE_MAX_S:
            return cached[1], f"GDACS is slow right now; using its data from {age / 60:.0f} min ago."
        raise
    _gdacs_cache[today] = (time.monotonic(), events)
    return events, None


def _matches(event: Event, point: tuple[float, float] | None, etype: str | None) -> bool:
    if etype and event.type != etype.lower():
        return False
    if point is None:
        return True
    return distance_km(event.center, point) - event.radius_km <= NEARBY_KM


def _result(req: EventQuery, events: list[Event], degraded: bool, notes: list[str]) -> EventResult:
    return EventResult(
        incident_id=req.incident_id,
        task_id=req.task_id,
        events=events,
        degraded=degraded,
        notes=" ".join(notes),
    )


async def _replay(req: EventQuery) -> list[Event]:
    point = known_place(req.location) if req.location else None
    if req.location and point is None:
        return []
    return [e for e in replay.replay_events() if _matches(e, point, req.type)]


async def handle(req: EventQuery) -> EventResult:
    started = time.perf_counter()

    if replay.enabled():
        events = await _replay(req)
        if events:
            return _result(
                req,
                events,
                False,
                ["Replay mode: recorded Cyclone Michaung (Dec 2023) with dates shifted to today."],
            )

    notes: list[str] = []
    degraded = False
    point: tuple[float, float] | None = None
    if req.location:
        try:
            point = await geocode(req.location)
        except GeocodeUnavailable:
            degraded = True
            notes.append(
                f"Location lookup is unavailable, so this shows all active events instead of only those near {req.location}."
            )
        else:
            if point is None:
                raise ServiceError(
                    ErrorCode.INVALID_INPUT.value,
                    f"Could not find a place called '{req.location}'. Try a city or state name.",
                    retryable=False,
                )

    jobs = [_gdacs_events()]
    if point:
        jobs.append(
            asyncio.wait_for(weather.fetch_events(*point, req.horizon_days), SOURCE_TIMEOUT_S)
        )
    results = await asyncio.gather(*jobs, return_exceptions=True)

    events: list[Event] = []
    gdacs_result = results[0]
    if isinstance(gdacs_result, BaseException):
        degraded = True
        logger.warning("gdacs failed: %r", gdacs_result)
        notes.append("GDACS disaster feed is unavailable right now; using weather forecasts only.")
    else:
        gdacs_events, gdacs_note = gdacs_result
        events += [with_severity_bonus(e) for e in gdacs_events]
        if gdacs_note:
            notes.append(gdacs_note)

    if point:
        weather_result = results[1]
        if isinstance(weather_result, BaseException):
            degraded = True
            logger.warning("open-meteo failed: %r", weather_result)
            notes.append("Weather forecast service is unavailable right now.")
        else:
            events += weather_result

    events = dedupe([e for e in events if _matches(e, point, req.type)])
    if not events and not degraded:
        notes.append("No active disruption events found near this location.")

    logger.info(
        "sentinel done",
        extra={
            "incident_id": req.incident_id,
            "task_id": req.task_id,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "events": len(events),
            "degraded": degraded,
        },
    )
    return _result(req, events, degraded, notes)
