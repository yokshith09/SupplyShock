"""Terminal chat with the Orchestrator logic (no ASI:One needed).

Run:  python scripts/chat_cli.py          (interactive)
      python scripts/chat_cli.py "Cyclone warning on the Tamil Nadu coast, are we exposed?" --yes
M1: sequential flow in DISPATCH_MODE=mock. The parallel executor replaces this loop in M2.
"""
import argparse
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

from agents.orchestrator import render  # noqa: E402
from agents.orchestrator.intents import classify  # noqa: E402
from agents.orchestrator.planner import build_plan, execution_order  # noqa: E402
from agents.orchestrator.prompts import HELP_TEXT  # noqa: E402
from agents.orchestrator.session import SessionStore  # noqa: E402
from shared import dispatch  # noqa: E402
from shared.constants import Intent  # noqa: E402
from shared.models import (  # noqa: E402
    ActionRequest, EventQuery, ExposureRequest, SourcingRequest, StrategyRequest)

store = SessionStore()


async def run_event_impact(s, plan, approve) -> None:
    iid, ids = s.incident_id, {}
    for layer in execution_order(plan):
        for t in layer:
            if t.agent == "sentinel":
                r = await dispatch.call("sentinel", EventQuery(
                    incident_id=iid, task_id=t.id, location=t.args.get("location"), type=t.args.get("type")))
                if not r.events:
                    print("No matching event found. Describe the event and where it is.")
                    return
                s.event = r.events[0]
                print(render.event_text(s.event))
            elif t.agent == "exposure" and t.action == "compute":
                s.exposure = await dispatch.call("exposure", ExposureRequest(incident_id=iid, task_id=t.id, event=s.event))
                print(render.exposure_text(s.exposure))
            elif t.agent == "sourcing":
                s.sourcing = await dispatch.call("sourcing", SourcingRequest(
                    incident_id=iid, task_id=t.id, exclude_zone=s.event,
                    material_ids=[m.material_id for m in s.exposure.materials]))
                print(f"Alternates found: {len(s.sourcing.alternates)} (search radius {s.sourcing.search_radius_km:.0f} km)")
            elif t.agent == "exposure" and t.action == "stock_cover":
                pass  # same data as compute in mock mode; real stock-cover call arrives with D2's Exposure
            elif t.agent == "strategy":
                res = await dispatch.call("strategy", StrategyRequest(
                    incident_id=iid, task_id=t.id, exposure=s.exposure, sourcing=s.sourcing))
                s.options = res.options
                print(render.options_text(s.options))
            elif t.agent == "human":
                rec = next((o for o in s.options if o.recommended), s.options[0])
                if not approve(rec):
                    print("Not approved. No actions taken.")
                    s.plan_state = "CLOSED"
                    return
            elif t.agent == "action":
                rec = next((o for o in s.options if o.recommended), s.options[0])
                s.receipt = await dispatch.call("action", ActionRequest(
                    incident_id=iid, task_id=t.id, option=rec, approved_by=s.sender))
                print(render.receipt_text(s.receipt))
    s.plan_state = "CLOSED"


async def handle(sender: str, text: str, yes: bool = False) -> None:
    s = store.get(sender)
    r = await classify(text)
    print(f"[intent: {r.intent.value} via {r.source}; location={r.location} type={r.event_type} "
          f"supplier={r.supplier_id} material={r.material}]")
    if r.intent == Intent.HELP:
        print(HELP_TEXT)
        return
    plan = build_plan(r)
    s.plan, s.plan_state, s.incident_id = plan, "PLANNED", str(uuid.uuid4())
    print(render.plan_text(plan))
    if r.intent == Intent.EVENT_IMPACT:
        def approve(opt):
            if yes:
                print(f"Auto-approved {opt.option_id} (--yes)")
                return True
            return input(f"Approve option {opt.option_id} ({opt.label})? (y/n) ").strip().lower().startswith("y")
        await run_event_impact(s, plan, approve)
    else:
        print("(M1: only EVENT_IMPACT is wired in the CLI; other intents are planned only.)")


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("message", nargs="?")
    ap.add_argument("--yes", action="store_true", help="auto-approve the recommended option")
    a = ap.parse_args()
    if a.message:
        asyncio.run(handle("cli-user", a.message, a.yes))
        return
    print("SupplyShock CLI (type 'quit' to exit)")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in ("quit", "exit"):
            break
        if text:
            asyncio.run(handle("cli-user", text, a.yes))


if __name__ == "__main__":
    main()
