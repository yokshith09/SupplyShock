"""The seed must reproduce the demo story for the Cyclone Michaung replay event."""

import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data import db, seed_generator  # noqa: E402
from shared.geo import distance_km, within_radius  # noqa: E402

TODAY = date(2026, 10, 24)
CENTER = (13.08, 80.27)
RADIUS_KM = 150
DISRUPTION_DAYS = 14
FIXTURES = ROOT / "tests" / "fixtures" / "contracts"


@pytest.fixture(scope="module")
def seeded(tmp_path_factory):
    path = tmp_path_factory.mktemp("db") / "supplyshock.db"
    start = time.perf_counter()
    seed_generator.build(path, today=TODAY)
    elapsed = time.perf_counter() - start
    mp = pytest.MonkeyPatch()
    mp.setenv("DB_PATH", str(path))
    yield elapsed
    mp.undo()


def hit_suppliers():
    return [s for s in db.list_suppliers() if within_radius((s["lat"], s["lon"]), CENTER, RADIUS_KM)]


def story_materials():
    return sorted(
        {m["id"] for s in hit_suppliers() for m in db.materials_for_supplier(s["id"])}
    )


def orders_at_risk():
    products = {p["id"] for m in story_materials() for p in db.products_using_material(m)}
    cutoff = (TODAY + timedelta(days=DISRUPTION_DAYS)).isoformat()
    return [o for o in db.open_orders_for_products(sorted(products)) if o["due_date"] < cutoff]


def test_builds_fast(seeded):
    assert seeded < 5


def test_row_counts(seeded):
    with db.get_connection() as conn:
        count = lambda t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]  # noqa: E731
        assert count("suppliers") == 25
        assert count("materials") == 30
        assert count("products") == 8
        assert count("customer_orders") == 40


def test_exactly_three_suppliers_hit(seeded):
    assert [s["id"] for s in hit_suppliers()] == ["S-03", "S-07", "S-11"]


def test_five_primary_materials(seeded):
    assert story_materials() == ["M-04", "M-07", "M-12", "M-15", "M-22"]


def test_twelve_orders_worth_1_82_crore(seeded):
    orders = orders_at_risk()
    assert len(orders) == 12
    assert sum(o["value_inr"] for o in orders) == pytest.approx(18_200_000, rel=0.03)


def test_orders_match_exposure_fixture(seeded):
    fixture = json.loads((FIXTURES / "ExposureReport.json").read_text(encoding="utf-8"))
    assert sorted(o["id"] for o in orders_at_risk()) == sorted(fixture["orders_at_risk"])
    assert sum(o["value_inr"] for o in orders_at_risk()) == fixture["revenue_at_risk_inr"]


def test_cover_days_match_story(seeded):
    expected = {"M-12": 6, "M-07": 9, "M-15": 11, "M-04": 18, "M-22": 25}
    for mat, days in expected.items():
        inv = db.inventory_for(mat)
        assert inv["on_hand_qty"] / inv["daily_consumption"] == days, mat


def test_m12_alternates(seeded):
    hit = {s["id"] for s in hit_suppliers()}
    alternates = [s for s in db.suppliers_for_material("M-12") if s["id"] not in hit]
    assert {s["id"] for s in alternates} == {"S-21", "S-14"}
    assert min(alternates, key=lambda s: s["price_inr"])["id"] == "S-21"


def test_coimbatore_outside_zone(seeded):
    s14 = db.get_supplier("S-14")
    assert distance_km((s14["lat"], s14["lon"]), CENTER) > RADIUS_KM * 1.2


def test_lookup_functions(seeded):
    assert db.get_supplier("S-21")["email"] == "s21@supplyshock.demo"
    assert db.get_supplier("S-99") is None
    assert db.get_material("M-12")["name"].startswith("ECU housing")
    assert db.get_order("O-1007")["product_id"] == "P-01"
    assert db.open_orders_for_products([]) == []
