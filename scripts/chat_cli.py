"""Terminal chat with the Orchestrator logic (no ASI:One needed).

Run:  python scripts/chat_cli.py          (interactive)
      python scripts/chat_cli.py "Cyclone warning on the Tamil Nadu coast, are we exposed?" --yes
Dispatch: DISPATCH_MODE=mock (default). To use D2's real services as they land:
      set DISPATCH_LOCAL_AGENTS=sentinel,exposure      (PowerShell: $env:DISPATCH_LOCAL_AGENTS="sentinel,exposure")
"""
import argparse
import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("LOG_LEVEL", "WARNING")  # quiet JSON logs in the CLI; set LOG_LEVEL=INFO to see them

from dotenv import load_dotenv  # noqa: E402

from agents.orchestrator import render  # noqa: E402
from agents.orchestrator.dispatcher import chosen_option, fallback, make_runner  # noqa: E402
from agents.orchestrator.executor import DagRun  # noqa: E402
from agents.orchestrator.intents import classify  # noqa: E402
from agents.orchestrator.planner import build_plan  # noqa: E402
from agents.orchestrator.prompts import HELP_TEXT  # noqa: E402
from agents.orchestrator.session import SessionStore  # noqa: E402
from shared.constants import Intent  # noqa: E402
from shared.models import ActionReceipt, EventResult, ExposureReport, SourcingResult, StrategyOptions  # noqa: E402

store = SessionStore()


def show(task, res) -> None:
    if isinstance(res, EventResult):
        print(render.event_text(res.events[0]))
    elif isinstance(res, ExposureReport) and task.action == "compute":
        print(render.exposure_text(res))
    elif isinstance(res, SourcingResult):
        print(f"Alternates found: {len(res.alternates)} (search radius {res.search_radius_km:.0f} km)"
              + (f"  [degraded: {res.notes}]" if res.degraded else ""))
    elif isinstance(res, StrategyOptions):
        print(render.options_text(res.options))
    elif isinstance(res, ActionReceipt):
        print(render.receipt_text(res))


async def handle(sender: str, text: str, yes: bool = False) -> None:
    s = store.get(sender)
    r = await classify(text)
    print(f"[intent: {r.intent.value} via {r.source}; location={r.location} type={r.event_type} "
          f"supplier={r.supplier_id} material={r.material}]")
    if r.intent == Intent.HELP:
        print(HELP_TEXT)
        return
    plan = build_plan(r)
    s.plan, s.incident_id, s.plan_state = plan, str(uuid.uuid4()), "PLANNED"
    print(render.plan_text(plan))
    if r.intent != Intent.EVENT_IMPACT:
        print("(Only EVENT_IMPACT is wired in the CLI; other intents are planned only.)")
        return
    run = DagRun(plan=plan, run_task=make_runner(s), fallback=fallback(s),
                 on_result=show, incident_id=s.incident_id)
    await run.run()
    if run.status == "AWAITING_APPROVAL":
        opt = chosen_option(s)
        ok = True if yes else input(
            f"Approve option {opt.option_id} ({opt.label})? (y/n) ").strip().lower().startswith("y")
        if yes:
            print(f"Auto-approved {opt.option_id} (--yes)")
        await run.resume(ok)
    s.plan_state = run.status
    if run.halt_message:
        print(run.halt_message)
    if run.errors:
        print(f"Some steps failed: {run.errors}")
    print(f"[plan status: {run.status}" + (f", degraded: {run.degraded}" if run.degraded else "") + "]")


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
