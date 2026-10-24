"""Template plans per intent, validated against an allow-list. LLM-drafted plans are not used yet."""
from pydantic import BaseModel

from agents.orchestrator.intents import IntentResult
from shared.constants import Intent

ALLOWED: dict[str, set[str]] = {
    "sentinel": {"resolve_event", "scan"},
    "exposure": {"compute", "stock_cover"},
    "sourcing": {"find_alternates"},
    "strategy": {"generate_options"},
    "action": {"execute"},
    "watchtower": {"subscribe"},
    "human": {"approve"},
}


class Task(BaseModel):
    id: str
    agent: str
    action: str
    args: dict = {}
    depends_on: list[str] = []


class Plan(BaseModel):
    intent: str
    tasks: list[Task]


class PlanError(ValueError):
    pass


def validate_plan(plan: Plan) -> Plan:
    ids = [t.id for t in plan.tasks]
    if len(set(ids)) != len(ids):
        raise PlanError("duplicate task ids")
    for t in plan.tasks:
        if t.agent not in ALLOWED or t.action not in ALLOWED[t.agent]:
            raise PlanError(f"task {t.id}: {t.agent}.{t.action} is not allowed")
        missing = [d for d in t.depends_on if d not in ids]
        if missing:
            raise PlanError(f"task {t.id}: unknown dependency {missing}")
    execution_order(plan)  # raises on cycles
    return plan


def execution_order(plan: Plan) -> list[list[Task]]:
    """Dependency layers; tasks in one layer can run in parallel."""
    done: set[str] = set()
    pending = list(plan.tasks)
    layers: list[list[Task]] = []
    while pending:
        ready = [t for t in pending if all(d in done for d in t.depends_on)]
        if not ready:
            raise PlanError("cycle in plan")
        layers.append(ready)
        done.update(t.id for t in ready)
        pending = [t for t in pending if t.id not in done]
    return layers


def build_plan(r: IntentResult) -> Plan:
    a = {"location": r.location, "type": r.event_type, "supplier_id": r.supplier_id, "material": r.material}
    if r.intent == Intent.EVENT_IMPACT:
        tasks = [
            Task(id="T1", agent="sentinel", action="resolve_event", args=a),
            Task(id="T2", agent="exposure", action="compute", depends_on=["T1"]),
            Task(id="T3", agent="sourcing", action="find_alternates", depends_on=["T2"]),
            Task(id="T4", agent="exposure", action="stock_cover", depends_on=["T2"]),
            Task(id="T5", agent="strategy", action="generate_options", depends_on=["T3", "T4"]),
            Task(id="T6", agent="human", action="approve", depends_on=["T5"]),
            Task(id="T7", agent="action", action="execute", depends_on=["T6"]),
        ]
    elif r.intent in (Intent.SCAN, Intent.SUPPLIER_CHECK):
        tasks = [
            Task(id="T1", agent="sentinel", action="scan", args=a),
            Task(id="T2", agent="exposure", action="compute", depends_on=["T1"]),
        ]
    elif r.intent == Intent.SOURCE_ALT:
        tasks = [Task(id="T1", agent="sourcing", action="find_alternates", args=a)]
    else:  # STATUS, HELP: answered directly, no specialist tasks
        tasks = []
    return validate_plan(Plan(intent=r.intent.value, tasks=tasks))
