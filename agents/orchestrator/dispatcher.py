"""Builds the typed request for each plan task, calls dispatch, and records results on the session."""
from agents.orchestrator.executor import HaltPlan
from agents.orchestrator.planner import Task
from agents.orchestrator.session import Session
from shared import dispatch
from shared.models import (
    ActionRequest, EventQuery, EventResult, ExposureRequest, ServiceError, SourcingRequest,
    SourcingResult, StrategyRequest, TaskError)


def _first(results: dict, task: Task, cls):
    for d in task.depends_on:
        if isinstance(results.get(d), cls):
            return results[d]
    for r in results.values():
        if isinstance(r, cls):
            return r
    return None


CLARIFY_CODES = {"INVALID_INPUT", "NOT_FOUND"}


def clarify_message(message: str) -> str:
    return (f"I couldn't use that: {message}\n"
            "Which city, port or region do you mean? For example: 'cyclone near Chennai'.")


def make_runner(session: Session, call=None):
    raw_call = call or dispatch.call
    iid = session.incident_id or ""

    async def call(agent, request, *a, **kw):  # noqa: F811 - wraps raw_call
        """Turn D2's INVALID_INPUT / NOT_FOUND into a question for the user instead of a failure."""
        try:
            res = await raw_call(agent, request, *a, **kw)
        except ServiceError as e:
            if e.code in CLARIFY_CODES:
                raise HaltPlan(clarify_message(e.message)) from e
            raise
        if isinstance(res, TaskError) and res.code in CLARIFY_CODES:
            raise HaltPlan(clarify_message(res.message))
        return res

    async def run_task(task: Task, results: dict):
        from shared.models import ExposureReport, StrategyOptions  # local import keeps top clean
        if task.agent == "sentinel":
            res = await call("sentinel", EventQuery(incident_id=iid, task_id=task.id,
                             location=task.args.get("location"), type=task.args.get("type")))
            if not res.events:
                raise HaltPlan("No matching event found. Tell me what happened and where, "
                               "for example: 'cyclone near Chennai'.")
            session.event = res.events[0]
            return res
        if task.agent == "exposure" and task.action == "stock_cover":
            # stock cover and stock-out dates are already part of the compute result
            rep = _first(results, task, ExposureReport)
            if rep is None:
                raise HaltPlan("No exposure data available.")
            return rep
        if task.agent == "exposure":
            ev = session.event or (_first(results, task, EventResult).events[0])
            res = await call("exposure", ExposureRequest(incident_id=iid, task_id=task.id, event=ev))
            session.exposure = res
            return res
        if task.agent == "sourcing":
            exp = session.exposure
            if exp is None:
                raise HaltPlan("This request needs an event first. Describe the disruption.")
            if not exp.suppliers_hit:
                raise HaltPlan("Good news: none of your suppliers are inside that event's impact zone.")
            res = await call("sourcing", SourcingRequest(
                incident_id=iid, task_id=task.id, exclude_zone=session.event,
                material_ids=[m.material_id for m in exp.materials]))
            session.sourcing = res
            return res
        if task.agent == "strategy":
            sourcing = session.sourcing or SourcingResult(incident_id=iid, task_id=task.id)
            res = await call("strategy", StrategyRequest(
                incident_id=iid, task_id=task.id, exposure=session.exposure, sourcing=sourcing))
            session.options = res.options
            return res
        if task.agent == "action":
            opt = chosen_option(session)
            res = await call("action", ActionRequest(
                incident_id=iid, task_id=task.id, option=opt, approved_by=session.sender))
            session.receipt = res
            return res
        raise ValueError(f"no runner for {task.agent}.{task.action}")

    return run_task


def chosen_option(session: Session):
    if not session.options:
        raise HaltPlan("There are no options to approve.")
    cid = getattr(session, "chosen_option_id", None)
    return next((o for o in session.options if o.option_id == cid),
                next((o for o in session.options if o.recommended), session.options[0]))


def fallback(session: Session):
    """Degraded results when a non-critical specialist is down."""
    iid = session.incident_id or ""

    def fb(task: Task, results: dict, err: Exception):
        if task.agent == "sourcing":
            res = SourcingResult(incident_id=iid, task_id=task.id, degraded=True,
                                 notes=f"Sourcing unavailable ({err!r}); using safety-stock options only.")
            session.sourcing = res
            return res
        return None

    return fb
