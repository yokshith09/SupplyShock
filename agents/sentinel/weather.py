"""Open-Meteo forecast -> low-confidence severe-weather Events. Owner: D2."""

from __future__ import annotations

import httpx

from shared.models import Event

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WIND_KMH = 60  # severe wind threshold
RAIN_MM = 100  # severe daily rain threshold
BASE_CONFIDENCE = 0.35


class WeatherError(Exception):
    pass


async def fetch_events(
    lat: float, lon: float, horizon_days: int = 7, timeout_s: float = 6
) -> list[Event]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "wind_speed_10m_max,precipitation_sum",
        "forecast_days": max(1, min(horizon_days, 16)),
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.get(FORECAST_URL, params=params)
            resp.raise_for_status()
            daily = resp.json()["daily"]
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise WeatherError(str(exc)) from exc

    days = daily.get("time") or []
    winds = daily.get("wind_speed_10m_max") or []
    rains = daily.get("precipitation_sum") or []
    bad = [
        (day, wind or 0.0, rain or 0.0)
        for day, wind, rain in zip(days, winds, rains)
        if (wind or 0) > WIND_KMH or (rain or 0) > RAIN_MM
    ]
    if not bad:
        return []

    max_wind = max(w for _, w, _ in bad)
    max_rain = max(r for _, _, r in bad)
    etype = "flood" if max_rain > RAIN_MM else "cyclone"
    severity = "Orange" if max_wind > 90 or max_rain > 200 else "Green"
    return [
        Event(
            event_id=f"METEO-{etype}-{lat:.2f}-{lon:.2f}-{bad[0][0]}",
            type=etype,
            title=f"Severe weather forecast: wind up to {max_wind:.0f} km/h, "
            f"rain up to {max_rain:.0f} mm/day",
            center={"lat": lat, "lon": lon},
            radius_km=100.0,
            severity=severity,
            start=bad[0][0],
            end=bad[-1][0],
            sources=["Open-Meteo"],
            confidence=BASE_CONFIDENCE,
        )
    ]
