import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agents.sourcing import ranker, service  # noqa: E402
from data import seed_generator  # noqa: E402
from shared.models import ServiceError, SourcingRequest, SourcingResult  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "contracts"
HIT = {"S-03", "S-07", "S-11"}


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def request(material_ids, **zone):
    base = fixture("SourcingRequest")
    return SourcingRequest.parse_obj(
        {**base, "material_ids": material_ids, "exclude_zone": {**base["exclude_zone"], **zone}}
    )


@pytest.fixture(autouse=True)
def seeded_db(tmp_path, monkeypatch):
    path = tmp_path / "supplyshock.db"
    seed_generator.build(path, today=date(2026, 10, 24))
    monkeypatch.setenv("DB_PATH", str(path))


async def test_fixture_request_matches_fixture_exactly():
    result = await service.handle(SourcingRequest.parse_obj(fixture("SourcingRequest")))
    assert isinstance(result, SourcingResult)
    assert result.dict() == fixture("SourcingResult")


async def test_s21_first_for_m12_and_no_hit_suppliers():
    result = await service.handle(request(["M-12"]))
    ids = [a.supplier_id for a in result.alternates]
    assert ids == ["S-21", "S-14"]
    assert not HIT & set(ids)


async def test_all_five_materials_widen_to_worldwide_for_m22():
    result = await service.handle(request(["M-12", "M-07", "M-15", "M-04", "M-22"]))
    by_material = {}
    for a in result.alternates:
        by_material.setdefault(a.material_id, []).append(a.supplier_id)
    assert by_material["M-04"] == ["S-22"]
    assert by_material["M-22"] == ["S-24"]
    assert result.search_radius_km == 0
    assert "M-22" in result.notes and "worldwide" in result.notes
    assert not result.degraded


async def test_national_widening(monkeypatch):
    # Pretend the cutoff is tiny: Pune (914 km) is no longer "nearby", but still in India.
    monkeypatch.setattr(service, "NEARBY_KM", 100.0)
    result = await service.handle(request(["M-12"]))
    assert [a.supplier_id for a in result.alternates] == ["S-21", "S-14"]
    assert "widened to suppliers in IN" in result.notes
    assert result.search_radius_km == 100.0


async def test_supplier_inside_a_bigger_zone_is_excluded():
    # 400 km x 1.2 = 480 km also swallows Coimbatore (427 km).
    result = await service.handle(request(["M-12"], radius_km=400))
    assert [a.supplier_id for a in result.alternates] == ["S-21"]


async def test_every_supplier_inside_zone():
    result = await service.handle(request(["M-12"], radius_km=2000))
    assert result.alternates == []
    assert "inside the impact zone" in result.notes


async def test_unknown_material_and_duplicates():
    result = await service.handle(request(["M-99", "M-07", "M-07"]))
    assert [a.supplier_id for a in result.alternates] == ["S-16"]
    assert "M-99" in result.notes


async def test_missing_database(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "nope.db"))
    with pytest.raises(ServiceError):
        await service.handle(request(["M-12"]))


def test_ranker_prefers_cheaper_when_other_factors_equal():
    base = {"lead_time_days": 7, "quality_rating": 0.8, "risk_score": 0.2}
    cheap = {**base, "id": "A", "price_inr": 100.0}
    pricey = {**base, "id": "B", "price_inr": 150.0}
    ranked = ranker.rank([pricey, cheap])
    assert [c["id"] for c, _ in ranked] == ["A", "B"]
    assert ranked[0][1] > ranked[1][1]


def test_ranker_top_n():
    cands = [
        {"id": str(i), "price_inr": 100.0 + i, "lead_time_days": 5, "quality_rating": 0.8, "risk_score": 0.2}
        for i in range(5)
    ]
    assert len(ranker.rank(cands)) == 3
