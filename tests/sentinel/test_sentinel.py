import json
import sys
from pathlib import Path

import httpx
import pytest
import respx
from tenacity import wait_none

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agents.sentinel import gdacs, service  # noqa: E402
from agents.sentinel.dedupe import dedupe  # noqa: E402
from shared.models import Event, EventQuery, ServiceError  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "contracts"
GDACS = gdacs.GDACS_URL
METEO = "https://api.open-meteo.com/v1/forecast"
GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def query(**kw):
    base = {"incident_id": "inc-1", "task_id": "T1"}
    return EventQuery(**{**base, **kw})


def feature(etype, eid, lat, lon, level="Orange", name="Test event", current="true"):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "eventtype": etype,
            "eventid": eid,
            "name": name,
            "alertlevel": level,
            "fromdate": "2026-10-22T00:00:00",
            "todate": "2026-10-25T00:00:00",
            "iscurrent": current,
            "country": "India",
        },
    }


def meteo(wind=10.0, rain=1.0):
    return httpx.Response(
        200,
        json={
            "daily": {
                "time": ["2026-10-24", "2026-10-25"],
                "wind_speed_10m_max": [wind, 12.0],
                "precipitation_sum": [rain, 0.0],
            }
        },
    )


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    service.clear_cache()
    monkeypatch.setenv("SEED_TODAY", "2026-10-24")
    monkeypatch.setenv("REPLAY_MODE", "false")
    monkeypatch.setattr(gdacs, "wait_exponential", lambda **_: wait_none())


async def test_replay_mode_matches_fixture(monkeypatch):
    monkeypatch.setenv("REPLAY_MODE", "true")
    req = EventQuery(**fixture("EventQuery"))
    result = await service.handle(req)
    expected = fixture("EventResult")
    assert result.incident_id == expected["incident_id"] and result.task_id == "T1"
    assert [e.model_dump() for e in result.events] == expected["events"]
    assert result.degraded is False


@respx.mock
async def test_replay_falls_through_to_live_for_other_places(monkeypatch):
    monkeypatch.setenv("REPLAY_MODE", "true")
    respx.get(GDACS).mock(return_value=httpx.Response(204))
    respx.get(METEO).mock(return_value=meteo())
    result = await service.handle(query(location="Pune"))
    assert result.events == [] and not result.degraded
    assert "No active disruption" in result.notes


@respx.mock
async def test_live_gdacs_keeps_only_nearby_events():
    respx.get(GDACS).mock(
        return_value=httpx.Response(
            200,
            json={
                "features": [
                    feature("TC", 1, 13.5, 81.0, "Orange", "Cyclone near Chennai"),
                    feature("EQ", 2, 32.38, 93.78, "Red", "Earthquake in China"),
                ]
            },
        )
    )
    respx.get(METEO).mock(return_value=meteo())
    result = await service.handle(query(location="Chennai"))
    assert [e.title for e in result.events] == ["Cyclone near Chennai"]
    event = result.events[0]
    assert event.type == "cyclone" and event.radius_km == 150
    assert event.confidence == pytest.approx(0.7)  # 0.6 base + Orange bonus
    assert event.center.lat == 13.5 and event.center.lon == 81.0
    assert result.degraded is False


@respx.mock
async def test_gdacs_down_is_degraded_not_a_crash():
    respx.get(GDACS).mock(return_value=httpx.Response(503))
    respx.get(METEO).mock(return_value=meteo(wind=95, rain=220))
    result = await service.handle(query(location="Chennai"))
    assert result.degraded is True
    assert "GDACS" in result.notes
    assert len(result.events) == 1 and result.events[0].sources == ["Open-Meteo"]
    assert result.events[0].type == "flood" and result.events[0].severity == "Orange"


@respx.mock
async def test_everything_down_returns_empty_degraded():
    respx.get(GDACS).mock(side_effect=httpx.ConnectError("down"))
    respx.get(METEO).mock(side_effect=httpx.ConnectError("down"))
    result = await service.handle(query(location="Chennai"))
    assert result.events == [] and result.degraded is True


@respx.mock
async def test_unknown_place_raises_invalid_input():
    respx.get(GEOCODE).mock(return_value=httpx.Response(200, json={"generationtime_ms": 0.1}))
    with pytest.raises(ServiceError) as exc:
        await service.handle(query(location="Atlantis"))
    assert exc.value.code == "INVALID_INPUT" and not exc.value.retryable


@respx.mock
async def test_geocoder_down_degrades_to_all_events():
    respx.get(GEOCODE).mock(side_effect=httpx.ConnectError("down"))
    respx.get(GDACS).mock(
        return_value=httpx.Response(200, json={"features": [feature("EQ", 2, 32.38, 93.78, "Red")]})
    )
    result = await service.handle(query(location="Some Small Town"))
    assert result.degraded is True and len(result.events) == 1


@respx.mock
async def test_gdacs_and_weather_for_same_storm_are_merged():
    respx.get(GDACS).mock(
        return_value=httpx.Response(200, json={"features": [feature("TC", 1, 13.2, 80.4, "Orange")]})
    )
    respx.get(METEO).mock(return_value=meteo(wind=80, rain=20))  # cyclone-type weather event
    result = await service.handle(query(location="Chennai"))
    assert len(result.events) == 1
    event = result.events[0]
    assert event.sources == ["GDACS", "Open-Meteo"]
    assert event.confidence == pytest.approx(0.85)  # 0.7 + 0.15 for the extra source


@respx.mock
async def test_type_filter_and_cache():
    route = respx.get(GDACS).mock(
        return_value=httpx.Response(
            200,
            json={"features": [feature("TC", 1, 13.2, 80.4), feature("FL", 3, 13.0, 80.2)]},
        )
    )
    respx.get(METEO).mock(return_value=meteo())
    first = await service.handle(query(location="Chennai", type="flood"))
    assert [e.type for e in first.events] == ["flood"]
    second = await service.handle(query(location="Pune"))  # different place, same cached feed
    assert route.call_count == 1 and second.events == []


@respx.mock
async def test_slow_gdacs_falls_back_to_stale_cache(monkeypatch):
    respx.get(METEO).mock(return_value=meteo())
    route = respx.get(GDACS).mock(
        return_value=httpx.Response(200, json={"features": [feature("TC", 1, 13.2, 80.4)]})
    )
    assert await service.refresh_gdacs() == 1
    monkeypatch.setattr(service, "CACHE_TTL_S", 0)  # force a refetch, which now fails
    route.mock(side_effect=httpx.ConnectError("down"))
    result = await service.handle(query(location="Chennai"))
    assert len(result.events) == 1 and not result.degraded
    assert "min ago" in result.notes


def test_dedupe_keeps_distant_events_apart():
    a = Event(event_id="a", type="flood", title="a", center={"lat": 13, "lon": 80}, radius_km=100,
              severity="Green", start="2026-10-24", sources=["GDACS"], confidence=0.6)  # fmt: skip
    b = Event(**{**a.dict(), "event_id": "b", "center": {"lat": 19, "lon": 73}})
    assert len(dedupe([a, b])) == 2
