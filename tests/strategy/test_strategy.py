import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agents.strategy import scoring, service  # noqa: E402
from data import seed_generator  # noqa: E402
from shared import llm  # noqa: E402
from shared.models import StrategyOptions, StrategyRequest  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "contracts"
ACTION_KEYS = {
    "rfq_email": {"type", "target_supplier_id", "material_id", "qty", "need_by"},
    "expedite_email": {"type", "target_supplier_id", "material_id", "qty"},
    "draft_po": {"type", "target_supplier_id", "material_id", "qty", "unit_price_inr"},
    "customer_notice": {"type", "order_id", "kind", "new_date"},
}


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def request(**changes) -> StrategyRequest:
    data = fixture("StrategyRequest")
    for key, value in changes.items():
        data[key] = {**data[key], **value}
    return StrategyRequest.parse_obj(data)


@pytest.fixture(autouse=True)
def seeded_db(tmp_path, monkeypatch):
    path = tmp_path / "supplyshock.db"
    seed_generator.build(path, today=date(2026, 10, 24))
    monkeypatch.setenv("DB_PATH", str(path))
    monkeypatch.setenv("SEED_TODAY", "2026-10-24")
    monkeypatch.setenv("STRATEGY_LLM", "false")


async def test_matches_fixture_exactly_with_template_rationale():
    result = await service.handle(request())
    assert isinstance(result, StrategyOptions)
    assert result.dict() == fixture("StrategyOptions")


async def test_story_shape():
    options = (await service.handle(request())).options
    assert [o.option_id for o in options] == ["OPT-A", "OPT-B", "OPT-C"]
    assert [o.option_id for o in options if o.recommended] == ["OPT-C"]
    assert [o.orders_saved for o in options] == [10, 11, 12]
    for option in options:
        for action in option.actions:
            assert set(action) == ACTION_KEYS[action["type"]], action


async def test_c_buys_from_s21_with_coimbatore_backup_quote():
    c = (await service.handle(request())).options[2]
    m12 = [a for a in c.actions if a.get("material_id") == "M-12"]
    assert {(a["type"], a["target_supplier_id"]) for a in m12} == {
        ("expedite_email", "S-03"), ("rfq_email", "S-21"), ("rfq_email", "S-14"), ("draft_po", "S-21"),
    }


async def test_lost_orders_get_delay_notices_with_dates():
    a = (await service.handle(request())).options[0]
    delays = [x for x in a.actions if x["type"] == "customer_notice" and x["kind"] == "delay"]
    assert {d["order_id"] for d in delays} == {"O-1019", "O-1028"}
    assert all(d["new_date"] == "2026-11-07" for d in delays)  # end of the 14-day disruption


async def test_llm_rationale_replaces_text_but_not_numbers(monkeypatch):
    monkeypatch.setenv("STRATEGY_LLM", "true")

    async def fake(messages, schema_hint, timeout_s=15):
        return {"OPT-A": "Fast but risky.", "OPT-B": "Cheaper, slower.", "OPT-C": "Best overall."}

    monkeypatch.setattr(llm, "complete_json", fake)
    with_llm = await service.handle(request())
    monkeypatch.setenv("STRATEGY_LLM", "false")
    without = await service.handle(request())
    assert [o.rationale for o in with_llm.options] == ["Fast but risky.", "Cheaper, slower.", "Best overall."]
    strip = lambda r: [{k: v for k, v in o.dict().items() if k != "rationale"} for o in r.options]  # noqa: E731
    assert strip(with_llm) == strip(without)
    assert not with_llm.degraded


async def test_llm_failure_falls_back_to_templates(monkeypatch):
    monkeypatch.setenv("STRATEGY_LLM", "true")

    async def broken(*args, **kwargs):
        raise llm.LLMError("down")

    monkeypatch.setattr(llm, "complete_json", broken)
    result = await service.handle(request())
    assert result.degraded is True and "standard wording" in result.notes
    assert [o.rationale for o in result.options] == [o["rationale"] for o in fixture("StrategyOptions")["options"]]


async def test_no_orders_at_risk_gives_no_options():
    result = await service.handle(request(exposure={"orders_at_risk": [], "materials": [], "suppliers_hit": []}))
    assert result.options == [] and "No orders are at risk" in result.notes


async def test_only_med_materials_needs_no_action():
    exposure = fixture("ExposureReport")
    meds = [m for m in exposure["materials"] if m["severity"] == "MED"]
    result = await service.handle(request(exposure={"materials": meds}))
    assert result.options == [] and "No action needed" in result.notes


async def test_missing_alternate_for_a_material():
    sourcing = fixture("SourcingResult")
    sourcing["alternates"] = [a for a in sourcing["alternates"] if a["material_id"] != "M-15"]
    result = await service.handle(request(sourcing={"alternates": sourcing["alternates"]}))
    b = result.options[1]
    assert "M-15" not in b.label
    assert sum(o.recommended for o in result.options) == 1


def test_disruption_days_from_trace():
    assert service.disruption_days(fixture("ExposureReport")["trace"]) == 14
    assert service.disruption_days(["Expected disruption for a Red flood: 15 days."]) == 15
    assert service.disruption_days([]) == 14


def test_scoring_weights():
    base = dict(orders_total=12, revenue_at_risk_inr=1e7, disruption_days=14)
    better = scoring.score(0.9, 12, cost_delta_inr=5e5, time_to_effect_days=2, **base)
    worse = scoring.score(0.5, 8, cost_delta_inr=5e5, time_to_effect_days=2, **base)
    assert better > worse
    assert scoring.score(0.9, 12, cost_delta_inr=5e5, time_to_effect_days=14, **base) < better
