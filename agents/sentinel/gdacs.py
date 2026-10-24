"""GDACS live disaster events -> Event. Owner: D2.

API: https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH (GeoJSON, no auth).
An empty result can come back as HTTP 204 / empty body.
"""

from __future__ import annotations

from datetime import date, timedelta

import httpx
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from shared.models import Event

GDACS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"

TYPE_MAP = {"TC": "cyclone", "FL": "flood", "EQ": "earthquake", "WF": "wildfire"}

# Impact radius (km) by event type and GDACS alert level.
RADIUS_KM = {
    "cyclone": {"Green": 100, "Orange": 150, "Red": 250},
    "flood": {"Green": 60, "Orange": 120, "Red": 200},
    "earthquake": {"Green": 50, "Orange": 100, "Red": 200},
    "wildfire": {"Green": 20, "Orange": 50, "Red": 100},
}
BASE_CONFIDENCE = 0.6


class GDACSError(Exception):
    pass


class _Retryable(Exception):
    pass


def _retryable(exc: BaseException) -> bool:
    return isinstance(exc, (httpx.TransportError, _Retryable))


def _center(geometry: dict) -> tuple[float, float] | None:
    coords = geometry.get("coordinates")
    if geometry.get("type") == "Point" and coords:
        return float(coords[1]), float(coords[0])
    # Polygon / MultiPolygon: average every vertex.
    flat: list[list[float]] = []

    def walk(node):
        if node and isinstance(node[0], (int, float)):
            flat.append(node)
        else:
            for child in node or []:
                walk(child)

    walk(coords)
    if not flat:
        return None
    return sum(p[1] for p in flat) / len(flat), sum(p[0] for p in flat) / len(flat)


def to_event(feature: dict) -> Event | None:
    props = feature.get("properties") or {}
    etype = TYPE_MAP.get(props.get("eventtype", ""))
    center = _center(feature.get("geometry") or {})
    if not etype or not center:
        return None
    level = props.get("alertlevel") or "Green"
    return Event(
        event_id=f"GDACS-{props.get('eventtype')}-{props.get('eventid')}",
        type=etype,
        title=props.get("name") or f"{etype.title()} ({props.get('country', 'unknown area')})",
        center={"lat": center[0], "lon": center[1]},
        radius_km=float(RADIUS_KM[etype].get(level, 100)),
        severity=level,
        start=(props.get("fromdate") or "")[:10],
        end=(props.get("todate") or "")[:10] or None,
        sources=["GDACS"],
        confidence=BASE_CONFIDENCE,
    )


async def fetch_events(today: date, lookback_days: int = 14, timeout_s: float = 6) -> list[Event]:
    """Active Orange/Red events from the last lookback_days. Raises GDACSError on failure."""
    params = {
        "eventlist": "TC;FL;EQ;WF",
        "alertlevel": "Orange;Red",
        "fromDate": (today - timedelta(days=lookback_days)).isoformat(),
        "toDate": today.isoformat(),
    }
    try:
        async with httpx.AsyncClient(
            timeout=timeout_s, headers={"User-Agent": "SupplyShock/0.1 (Fetch-A-Thon demo)"}
        ) as client:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=3),
                retry=retry_if_exception(_retryable),
                reraise=True,
            ):
                with attempt:
                    resp = await client.get(GDACS_URL, params=params)
                    if resp.status_code >= 500:
                        raise _Retryable(f"GDACS HTTP {resp.status_code}")
    except (httpx.HTTPError, _Retryable) as exc:
        raise GDACSError(str(exc)) from exc

    if resp.status_code == 204 or not resp.content.strip():
        return []
    if resp.status_code >= 400:
        raise GDACSError(f"GDACS HTTP {resp.status_code}")
    try:
        features = resp.json().get("features") or []
    except ValueError as exc:
        raise GDACSError("GDACS returned invalid JSON") from exc

    cutoff = (today - timedelta(days=2)).isoformat()
    events = []
    for feature in features:
        event = to_event(feature)
        if not event:
            continue
        is_current = str((feature.get("properties") or {}).get("iscurrent", "")).lower() == "true"
        if is_current or (event.end or event.start) >= cutoff:
            events.append(event)
    return events
