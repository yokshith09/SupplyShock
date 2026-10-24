import json
import sys
import time
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agents.exposure import cover, service  # noqa: E402
from data import seed_generator  # noqa: E402
from shared.models import Event, ExposureReport, ExposureRequest, ServiceError  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "contracts"


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def event(**kw):
    base = fixture("ExposureRequest")["event"]
    return Event.parse_obj({**base, **kw})


@pytest.fixture(autouse=True)
def seeded_db(tmp_path, monkeypatch):
    path = tmp_path / "supplyshock.db"
    seed_generator.build(path, today=date(2026, 10, 24))
    monkeypatch.setenv("DB_PATH", str(path))
    monkeypatch.setenv("SEED_TODAY", "2026-10-24")


async def test_michaung_matches_fixture_exactly():
    req = ExposureRequest.parse_obj(fixture("ExposureRequest"))
    start = time.perf_counter()
    report = await service.handle(req)
    assert time.perf_counter() - start < 1
    assert isinstance(report, ExposureReport)
    assert report.dict() == fixture("ExposureReport")


async def test_far_away_event_gives_zero_exposure():
    req = ExposureRequest(incident_id="i", task_id="T2", event=event(center={"lat": 35.68, "lon": 139.69}))
    report = await service.handle(req)
    assert report.suppliers_hit == [] and report.materials == [] and report.orders_at_risk == []
    assert report.revenue_at_risk_inr == 0
    assert "Closest is S-04 Shenzhen MicroTech" in report.trace[-1]


async def test_red_cyclone_lasts_longer_and_puts_more_orders_at_risk():
    orange = await service.handle(ExposureRequest(incident_id="i", task_id="T2", event=event()))
    red = await service.handle(ExposureRequest(incident_id="i", task_id="T2", event=event(severity="Red")))
    assert len(red.orders_at_risk) > len(orange.orders_at_risk)
    assert set(orange.orders_at_risk) <= set(red.orders_at_risk)
    assert "21 days" in " ".join(red.trace)


async def test_small_radius_hits_only_nearest_suppliers():
    # 10 km x 1.2 = 12 km: only Chennai Castings (12 km away) is inside.
    report = await service.handle(ExposureRequest(incident_id="i", task_id="T2", event=event(radius_km=10.5)))
    assert report.suppliers_hit == ["S-03"]
    assert {m.material_id for m in report.materials} == {"M-04", "M-12"}


async def test_missing_database_raises_service_error(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "nope.db"))
    with pytest.raises(ServiceError) as exc:
        await service.handle(ExposureRequest(incident_id="i", task_id="T2", event=event()))
    assert exc.value.code == "INTERNAL"


@pytest.mark.parametrize(
    "cov, disruption, alt, expected",
    [
        (6, 14, 7, "CRITICAL"),  # runs out before the fastest alternate can deliver
        (9, 14, 6, "HIGH"),  # alternate in time, but runs out during the disruption
        (18, 14, 8, "MED"),  # within 2x the disruption
        (40, 14, 8, "LOW"),
        (5, 14, None, "CRITICAL"),  # no alternate at all
        (20, 14, None, "MED"),
    ],
)
def test_severity_rules(cov, disruption, alt, expected):
    assert cover.severity(cov, disruption, alt) == expected


def test_disruption_days_table():
    assert cover.disruption_days("cyclone", "Orange") == 14
    assert cover.disruption_days("cyclone", "Red") == 21
    assert cover.disruption_days("strike", "Unknown") == 7
    assert cover.disruption_days("meteor", "Red") == cover.DEFAULT_DISRUPTION_DAYS


def test_inr_short():
    assert service.inr_short(18_200_000) == "Rs 1.82 Cr"
    assert service.inr_short(420_000) == "Rs 4.2 L"
    assert service.inr_short(9_500) == "Rs 9,500"
