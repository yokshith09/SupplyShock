import asyncio
import sqlite3
import sys
import time
import types

import pytest

from agents.orchestrator.executor import DagRun, HaltPlan, TaskFailed
from agents.orchestrator.intents import classify_keywords
from agents.orchestrator.dispatcher import fallback, make_runner
from agents.orchestrator.planner import Plan, Task, build_plan, plan_from_llm_json
from agents.orchestrator.session import Session
from agents.orchestrator.store import Store
from shared import dispatch
from shared.models import EventQuery, ServiceError, TaskError

FAST = dict(backoff_s=(0, 0))


def plan(*tasks):
    return Plan(intent="X", tasks=list(tasks))


def T(i, agent="sentinel", action="scan", deps=()):
    return Task(id=i, agent=agent, action=action, depends_on=list(deps))


def run(coro):
    return asyncio.run(coro)


def test_parallel_tasks_run_concurrently():
    async def rt(task, results):
        await asyncio.sleep(0.3)
        return task.id
    p = plan(T("T1"), T("T2", "exposure", "compute", ["T1"]), T("T3", "sourcing", "find_alternates", ["T2"]),
             T("T4", "exposure", "stock_cover", ["T2"]))
    t0 = time.perf_counter()
    r = run(DagRun(p, rt, **FAST).run())
    assert r.status == "CLOSED" and set(r.results) == {"T1", "T2", "T3", "T4"}
    assert time.perf_counter() - t0 < 1.1  # 3 layers of 0.3s, T3/T4 in parallel (4 serial would be 1.2s)


def test_retry_then_success():
    calls = {"n": 0}

    async def rt(task, results):
        calls["n"] += 1
        if calls["n"] < 3:
            raise TaskFailed("flaky")
        return "ok"
    r = run(DagRun(plan(T("T1")), rt, **FAST).run())
    assert calls["n"] == 3 and r.status == "CLOSED" and r.results["T1"] == "ok"


def test_timeout_retry_then_fallback_degraded():
    async def rt(task, results):
        await asyncio.sleep(1)
    fb = lambda task, results, err: types.SimpleNamespace(degraded=True, notes="fallback")  # noqa: E731
    r = run(DagRun(plan(T("T1")), rt, fallback=fb, timeout_s=0.05, retries=2, **FAST).run())
    assert r.status == "DEGRADED" and r.degraded == ["T1"] and r.results["T1"].notes == "fallback"


def test_failure_without_fallback_skips_dependents():
    async def rt(task, results):
        raise TaskFailed("down", retryable=False)
    r = run(DagRun(plan(T("T1"), T("T2", "exposure", "compute", ["T1"])), rt, **FAST).run())
    assert r.status == "FAILED" and "T1" in r.errors and "T2" not in r.results


def test_task_error_response_counts_as_failure():
    async def rt(task, results):
        return TaskError(incident_id="i", task_id="T1", code="UPSTREAM_API", message="x", retryable=False)
    r = run(DagRun(plan(T("T1")), rt, **FAST).run())
    assert r.status == "FAILED"


def test_halt_plan_stops_cleanly():
    async def rt(task, results):
        if task.id == "T1":
            raise HaltPlan("nothing to do")
        return "x"
    r = run(DagRun(plan(T("T1"), T("T2", "exposure", "compute", ["T1"])), rt, **FAST).run())
    assert r.status == "CLOSED" and r.halt_message == "nothing to do" and "T2" not in r.results


def test_human_gate_pause_and_resume():
    seen = []

    async def rt(task, results):
        seen.append(task.id)
        return task.id
    p = plan(T("T1"), T("T6", "human", "approve", ["T1"]), T("T7", "action", "execute", ["T6"]))
    r = run(DagRun(p, rt, **FAST).run())
    assert r.status == "AWAITING_APPROVAL" and seen == ["T1"]
    r = run(r.resume(True))
    assert r.status == "CLOSED" and seen == ["T1", "T7"]


def test_human_gate_reject_runs_nothing():
    seen = []

    async def rt(task, results):
        seen.append(task.id)
    p = plan(T("T6", "human", "approve"), T("T7", "action", "execute", ["T6"]))
    r = run(DagRun(p, rt, **FAST).run())
    r = run(r.resume(False))
    assert r.status == "CLOSED" and seen == [] and "Not approved" in r.halt_message


def test_replan_hook_adds_tasks():
    async def rt(task, results):
        return task.id

    def replan(task, res):
        return [T("T9", "exposure", "compute", ["T1"])] if task.id == "T1" else None
    r = run(DagRun(plan(T("T1")), rt, replan=replan, **FAST).run())
    assert set(r.results) == {"T1", "T9"}


def test_invalid_llm_plan_falls_back_to_template():
    ir = classify_keywords("Cyclone warning on the Tamil Nadu coast, are we exposed?")
    assert plan_from_llm_json("not json", ir).tasks == build_plan(ir).tasks
    bad = Plan(intent="EVENT_IMPACT", tasks=[T("T1", "hacker", "run")]).model_dump_json()
    assert plan_from_llm_json(bad, ir).tasks == build_plan(ir).tasks
    good = build_plan(ir).model_dump_json()
    assert plan_from_llm_json(good, ir).tasks == build_plan(ir).tasks


def test_full_event_flow_in_mock_mode(monkeypatch):
    monkeypatch.setenv("DISPATCH_MODE", "mock")
    s = Session(sender="u", incident_id="inc-1")
    ir = classify_keywords("Cyclone warning on the Tamil Nadu coast, are we exposed?")
    dr = DagRun(build_plan(ir), make_runner(s), fallback=fallback(s), incident_id="inc-1", **FAST)
    run(dr.run())
    assert dr.status == "AWAITING_APPROVAL" and s.exposure.revenue_at_risk_inr > 1e7
    run(dr.resume(True))
    assert dr.status == "CLOSED" and s.receipt and s.receipt.results


def test_sourcing_down_degrades_but_flow_completes(monkeypatch):
    monkeypatch.setenv("DISPATCH_MODE", "mock")
    real = dispatch.call

    async def flaky(agent, request, timeout_s=20):
        if agent == "sourcing":
            raise TaskFailed("sourcing killed")
        return await real(agent, request, timeout_s)
    s = Session(sender="u", incident_id="inc-2")
    ir = classify_keywords("Cyclone warning on the Tamil Nadu coast, are we exposed?")
    dr = DagRun(build_plan(ir), make_runner(s, flaky), fallback=fallback(s), incident_id="inc-2", **FAST)
    run(dr.run())
    assert dr.status == "AWAITING_APPROVAL" and dr.degraded == ["T3"] and s.options


def test_local_dispatch_uses_service_and_converts_service_error(monkeypatch):
    calls = []
    mod = types.ModuleType("agents.sentinel.service")

    async def handle(req):
        calls.append(req.task_id)
        raise ServiceError("UPSTREAM_API", "gdacs down", True)
    mod.handle = handle
    monkeypatch.setitem(sys.modules, "agents.sentinel.service", mod)
    monkeypatch.setenv("DISPATCH_MODE", "mock")
    monkeypatch.setenv("DISPATCH_LOCAL_AGENTS", "sentinel")
    res = run(dispatch.call("sentinel", EventQuery(incident_id="i", task_id="T1")))
    assert calls == ["T1"] and isinstance(res, TaskError) and res.code == "UPSTREAM_API" and res.retryable
    # other agents stay on fixtures
    assert dispatch.mode_for("exposure") == "mock"


def test_local_dispatch_missing_service_is_clear(monkeypatch):
    monkeypatch.setitem(sys.modules, "agents.sourcing.service", None)  # forces ImportError
    monkeypatch.setenv("DISPATCH_MODE", "local")
    with pytest.raises(ModuleNotFoundError, match="service.py"):
        run(dispatch.call("sourcing", EventQuery(incident_id="i", task_id="T1")))


def test_store_roundtrip_in_memory():
    conn = sqlite3.connect(":memory:")
    st = Store(lambda: conn)
    st.save_incident({"id": "inc-1", "event": {"t": 1}, "status": "OPEN"})
    st.save_incident({"id": "inc-1", "event": {"t": 1}, "status": "CLOSED", "outcome": "done"})
    st.log_action("inc-1", {"type": "rfq_email", "target": "S-21", "status": "done"})
    assert conn.execute("select status from incidents where id='inc-1'").fetchone()[0] == "CLOSED"
    assert st.list_actions("inc-1")[0]["target"] == "S-21"


@pytest.mark.parametrize("mode", ["service_error", "task_error"])
def test_invalid_place_becomes_clarifying_question(monkeypatch, mode):
    monkeypatch.setenv("DISPATCH_MODE", "mock")

    async def bad_place(agent, request, timeout_s=20):
        if mode == "service_error":
            raise ServiceError("INVALID_INPUT", "unknown place 'Atlantis'")
        return TaskError(incident_id="i", task_id=request.task_id, code="INVALID_INPUT",
                         message="unknown place 'Atlantis'", retryable=False)
    s = Session(sender="u", incident_id="inc-3")
    ir = classify_keywords("Cyclone warning near Chennai, are we exposed?")
    dr = DagRun(build_plan(ir), make_runner(s, bad_place), fallback=fallback(s), incident_id="inc-3", **FAST)
    run(dr.run())
    assert dr.status == "CLOSED" and not dr.errors
    assert "Atlantis" in dr.halt_message and "Which city" in dr.halt_message
