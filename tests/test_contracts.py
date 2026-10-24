"""Contract tests: fixtures <-> shared/models.py, plus demo-story consistency.

The story checks always run. The model checks skip until D1 merges shared/models.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "contracts"
sys.path.insert(0, str(ROOT))

MODEL_NAMES = [
    "EventQuery", "EventResult", "ExposureRequest", "ExposureReport",
    "SourcingRequest", "SourcingResult", "StrategyRequest", "StrategyOptions",
    "ActionRequest", "ActionReceipt", "WatchSubscribe", "WatchAlert", "TaskError",
]  # fmt: skip

ACTION_KEYS = {
    "rfq_email": {"type", "target_supplier_id", "material_id", "qty", "need_by"},
    "expedite_email": {"type", "target_supplier_id", "material_id", "qty"},
    "draft_po": {"type", "target_supplier_id", "material_id", "qty", "unit_price_inr"},
    "customer_notice": {"type", "order_id", "kind", "new_date"},
}


def load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))


# --- story consistency (always runs) ---------------------------------------


def test_every_model_has_a_fixture():
    missing = [n for n in MODEL_NAMES if not (FIXTURE_DIR / f"{n}.json").exists()]
    assert not missing, f"missing fixtures: {missing}"


def test_single_incident_id():
    ids = {load(n)["incident_id"] for n in MODEL_NAMES}
    assert len(ids) == 1, ids


def test_responses_echo_request_task_ids():
    pairs = [
        ("EventQuery", "EventResult"),
        ("ExposureRequest", "ExposureReport"),
        ("SourcingRequest", "SourcingResult"),
        ("StrategyRequest", "StrategyOptions"),
        ("ActionRequest", "ActionReceipt"),
    ]
    for req, resp in pairs:
        assert load(req)["task_id"] == load(resp)["task_id"], (req, resp)


def test_responses_have_degraded_and_notes():
    for name in ["EventResult", "ExposureReport", "SourcingResult", "StrategyOptions", "ActionReceipt"]:
        data = load(name)
        assert data["degraded"] is False and "notes" in data, name


def test_exposure_matches_demo_story():
    report = load("ExposureReport")
    assert report["suppliers_hit"] == ["S-03", "S-07", "S-11"]
    assert len(report["materials"]) == 5
    assert len(report["orders_at_risk"]) == 12 == len(set(report["orders_at_risk"]))
    assert report["revenue_at_risk_inr"] == pytest.approx(18_200_000, rel=0.03)
    m12 = next(m for m in report["materials"] if m["material_id"] == "M-12")
    assert m12["cover_days"] == 6.0 and m12["severity"] == "CRITICAL"
    assert m12["stockout_date"] == "2026-10-30"


def test_sourcing_excludes_hit_suppliers_and_ranks_s21_first_for_m12():
    hit = set(load("ExposureReport")["suppliers_hit"])
    alternates = load("SourcingResult")["alternates"]
    assert not hit & {a["supplier_id"] for a in alternates}
    m12 = sorted((a for a in alternates if a["material_id"] == "M-12"), key=lambda a: -a["score"])
    assert m12[0]["supplier_id"] == "S-21"
    assert "S-14" in {a["supplier_id"] for a in m12}


def test_strategy_options_and_actions():
    options = load("StrategyOptions")["options"]
    assert [o["option_id"] for o in options] == ["OPT-A", "OPT-B", "OPT-C"]
    recommended = [o for o in options if o["recommended"]]
    assert [o["option_id"] for o in recommended] == ["OPT-C"]
    for option in options:
        for action in option["actions"]:
            assert set(action) == ACTION_KEYS[action["type"]], action


def test_action_request_carries_recommended_option():
    recommended = next(o for o in load("StrategyOptions")["options"] if o["recommended"])
    assert load("ActionRequest")["option"] == recommended
    receipt_targets = [(r["type"], r["target"]) for r in load("ActionReceipt")["results"]]
    expected = [
        (a["type"], a.get("target_supplier_id") or a.get("order_id"))
        for a in recommended["actions"]
    ]
    assert receipt_targets == expected


def test_embedded_objects_match_their_own_fixtures():
    event = load("EventResult")["events"][0]
    assert load("ExposureRequest")["event"] == event
    assert load("SourcingRequest")["exclude_zone"] == event
    assert load("WatchSubscribe")["event"] == event
    strategy_req = load("StrategyRequest")
    assert strategy_req["exposure"] == load("ExposureReport")
    assert strategy_req["sourcing"] == load("SourcingResult")


# --- fixtures <-> shared/models.py (skips until D1 merges the models) ---------


@pytest.mark.parametrize("name", MODEL_NAMES)
def test_fixture_validates_against_model(name: str):
    models = pytest.importorskip(
        "shared.models", reason="shared/models.py not on main yet (D1, Phase 0)"
    )
    model_cls = getattr(models, name, None)
    assert model_cls is not None, f"shared.models has no {name}"
    data = load(name)
    if hasattr(model_cls, "model_validate"):
        model_cls.model_validate(data)
    else:
        model_cls.parse_obj(data)
