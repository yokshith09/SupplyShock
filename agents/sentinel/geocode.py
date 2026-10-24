"""Place name -> (lat, lon). Built-in places first so the demo never depends on the API. Owner: D2."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("supplyshock.sentinel.geocode")

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Longest keys are matched first ("tamil nadu coast" before "tamil nadu").
KNOWN_PLACES: dict[str, tuple[float, float]] = {
    "tamil nadu coast": (13.08, 80.27),
    "tamil nadu": (13.08, 80.27),
    "chennai": (13.08, 80.27),
    "madras": (13.08, 80.27),
    "ennore": (13.21, 80.32),
    "sriperumbudur": (12.97, 79.94),
    "coimbatore": (11.02, 76.96),
    "bengaluru": (12.97, 77.59),
    "bangalore": (12.97, 77.59),
    "pune": (18.52, 73.86),
    "gujarat": (23.02, 72.57),
    "ahmedabad": (23.02, 72.57),
    "shenzhen": (22.54, 114.06),
    "penang": (5.41, 100.33),
    "stuttgart": (48.78, 9.18),
    "monterrey": (25.69, -100.32),
}


class GeocodeUnavailable(Exception):
    """The geocoding API could not be reached (not the same as 'place not found')."""


def known_place(text: str) -> tuple[float, float] | None:
    lowered = text.lower()
    for key in sorted(KNOWN_PLACES, key=len, reverse=True):
        if key in lowered:
            return KNOWN_PLACES[key]
    return None


async def geocode(text: str, timeout_s: float = 6) -> tuple[float, float] | None:
    """Return (lat, lon), or None if the place is unknown.

    Raises GeocodeUnavailable if the API fails, so callers can degrade instead of
    telling the user the place doesn't exist.
    """
    hit = known_place(text)
    if hit:
        return hit
    name = text.replace(" coast", "").strip()
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.get(GEOCODE_URL, params={"name": name, "count": 1})
            resp.raise_for_status()
            results = resp.json().get("results") or []
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("geocoding failed for %r: %s", name, exc)
        raise GeocodeUnavailable(str(exc)) from exc
    if not results:
        return None
    return float(results[0]["latitude"]), float(results[0]["longitude"])
