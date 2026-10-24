import asyncio

import pytest

from agents.orchestrator.intents import classify_keywords
from agents.orchestrator.planner import Plan, PlanError, Task, build_plan, execution_order, validate_plan
from agents.orchestrator.render import exposure_text, inr, options_text, plan_text, receipt_text
from shared import dispatch
from shared.constants import Intent
from shared.models import EventQuery, ExposureReport, StrategyOptions, ActionReceipt

DEMO = "Cyclone warning on the Tamil Nadu coast, are we exposed?"


def test_demo_sentence():
    r = classify_keywords(DEMO)
    assert r.intent == Intent.EVENT_IMPACT
    assert r.event_type == "cyclone" and r.location == "Chennai"


@pytest.mark.parametrize("text,intent", [
    ("Are we exposed to anything right now?", Intent.SCAN),
    (DEMO, Intent.EVENT_IMPACT),
    ("Is supplier S-07 safe right now?", Intent.SUPPLIER_CHECK),
    ("Find a backup supplier for ECU housings.", Intent.SOURCE_ALT),
    ("Update on the Chennai incident?", Intent.STATUS),
    ("hello", Intent.HELP),
])
def test_all_intents(text, intent):
    assert classify_keywords(text).intent == intent


def test_supplier_entity():
    assert classify_keywords("Is supplier s-7 safe?").supplier_id == "S-07"


def test_event_plan_is_valid_and_parallel():
    plan = build_plan(classify_keywords(DEMO))
    layers = [sorted(t.id for t in layer) for layer in execution_order(plan)]
    assert layers == [["T1"], ["T2"], ["T3", "T4"], ["T5"], ["T6"], ["T7"]]
    assert plan_text(plan)


def test_planner_rejects_unknown_agent_and_cycle():
    with pytest.raises(PlanError):
        validate_plan(Plan(intent="X", tasks=[Task(id="T1", agent="hacker", action="run")]))
    with pytest.raises(PlanError):
        validate_plan(Plan(intent="X", tasks=[
            Task(id="T1", agent="sentinel", action="scan", depends_on=["T2"]),
            Task(id="T2", agent="exposure", action="compute", depends_on=["T1"])]))


def test_dispatch_mock_copies_ids_and_validates(monkeypatch):
    monkeypatch.setenv("DISPATCH_MODE", "mock")
    req = EventQuery(incident_id="inc-1", task_id="T1", location="Chennai")
    res = asyncio.run(dispatch.call("sentinel", req))
    assert (res.incident_id, res.task_id) == ("inc-1", "T1") and res.events
    ex = asyncio.run(dispatch.call("exposure", req))
    assert isinstance(ex, ExposureReport) and ex.task_id == "T1"
    assert isinstance(asyncio.run(dispatch.call("strategy", req)), StrategyOptions)
    assert isinstance(asyncio.run(dispatch.call("action", req)), ActionReceipt)


def test_dispatch_other_modes_not_ready(monkeypatch):
    monkeypatch.setenv("DISPATCH_MODE", "remote")
    with pytest.raises(NotImplementedError):
        asyncio.run(dispatch.call("sentinel", EventQuery(incident_id="i", task_id="T1")))


def test_renderers_never_empty(monkeypatch):
    monkeypatch.setenv("DISPATCH_MODE", "mock")
    req = EventQuery(incident_id="i", task_id="T1")
    ex = asyncio.run(dispatch.call("exposure", req))
    opts = asyncio.run(dispatch.call("strategy", req)).options
    rc = asyncio.run(dispatch.call("action", req))
    assert exposure_text(ex) and options_text(opts) and receipt_text(rc)
    assert inr(18_200_000) == "₹1.82 Cr"
