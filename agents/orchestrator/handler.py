"""Orchestrator conversation logic: text/card-selection in -> list of Replies out. No uagents import,
so it is unit-testable. agent.py only converts Replies into ChatMessages.

Flow: request -> plan runs to the approval gate (event, exposure, sourcing, options) -> options carousel ->
pick -> review card -> approve -> Action agent -> receipt. Every step also works with typed text
("select OPT-C", "approve", "cancel") for clients that do not render cards.
"""
import asyncio
import dataclasses
import json
import re
import uuid

from agents.orchestrator import cards, render
from agents.orchestrator.cards import Reply
from agents.orchestrator.dispatcher import chosen_option, fallback, make_runner
from agents.orchestrator.executor import DagRun
from agents.orchestrator.intents import classify
from agents.orchestrator.planner import build_plan
from agents.orchestrator.prompts import HELP_TEXT
from agents.orchestrator.session import Session, SessionStore
from shared.constants import Intent
from shared.logging import get_logger, log_task

log = get_logger("orchestrator")

KNOWN_ACTIONS = {"pick_option", "approve", "cancel", "done", "new_scan"}
START_HINT = "Try: 'Cyclone warning on the Tamil Nadu coast, are we exposed?'"


def parse_selection(text: str) -> dict:
    """Card clicks arrive as JSON (direct) or as prose (planner-mediated). Handle both, plus typed commands."""
    try:
        d = json.loads(text)
        if isinstance(d, dict):
            return d
    except (ValueError, TypeError):
        pass
    t = text.lower()
    sel: dict = {}
    m = re.search(r"\bopt[- ]?([a-z])\b", t) or re.search(r"\b(?:option|select|pick|choose)\s+([a-e])\b", t)
    if m:
        sel["option_id"] = f"OPT-{m.group(1).upper()}"
    if re.search(r"\b(approve|approved|confirm|confirmed|go ahead|proceed|execute)\b", t):
        sel["action"] = "approve"
    elif re.search(r"\b(cancel|cancelled|reject|rejected|abort|decline)\b", t):
        sel["action"] = "cancel"
    elif "option_id" in sel:
        sel["action"] = "pick_option"
    return sel


def _default_save(incident: dict) -> None:
    from agents.orchestrator.store import save_incident
    save_incident(incident)


class Orchestrator:
    def __init__(self, sessions: SessionStore | None = None, runner_factory=make_runner, save_incident=_default_save):
        self.sessions = sessions or SessionStore()
        self.runner_factory = runner_factory
        self.save_incident = save_incident
        self._locks: dict[str, asyncio.Lock] = {}

    async def on_text(self, sender: str, text: str) -> list[Reply]:
        lock = self._locks.setdefault(sender, asyncio.Lock())
        async with lock:  # one conversation step at a time per user (fast double-clicks)
            try:
                return await self._on_text(sender, (text or "").strip())
            except Exception as e:  # noqa: BLE001 - never leave the user without an answer
                log_task(log, f"unhandled: {e!r}", agent="orchestrator", status="error")
                return [Reply("Something went wrong on my side. Please try again in a moment.\n" + START_HINT)]

    # ---- routing -------------------------------------------------------------------------
    async def _on_text(self, sender: str, text: str) -> list[Reply]:
        if not text:
            return [Reply(HELP_TEXT)]
        s = self.sessions.get(sender)
        awaiting = s.run is not None and s.run.status == "AWAITING_APPROVAL"
        sel = parse_selection(text)
        action = sel.get("action")
        is_json = text.startswith("{")
        if action in ("done", "new_scan"):
            return [Reply(HELP_TEXT)]
        if action in KNOWN_ACTIONS and awaiting:
            return await self._selection(s, sel)
        if action in KNOWN_ACTIONS and is_json:
            return [Reply("That plan is no longer waiting for your approval. " + START_HINT)]
        return await self._new_request(s, text)

    async def _new_request(self, s: Session, text: str) -> list[Reply]:
        r = await classify(text)
        if r.intent == Intent.HELP:
            return [Reply(HELP_TEXT)]
        if r.intent == Intent.STATUS:
            return [Reply(self._status(s))]
        if r.intent in (Intent.SUPPLIER_CHECK, Intent.SOURCE_ALT):
            return [Reply("Supplier checks and standalone sourcing are not in this demo yet. "
                          "I can run a full disruption response: " + START_HINT)]
        if r.intent == Intent.SCAN:  # a scan is the full flow with whatever event the Sentinel finds
            r = dataclasses.replace(r, intent=Intent.EVENT_IMPACT)
        s = self.sessions.reset(s.sender)
        s.incident_id = str(uuid.uuid4())
        plan = build_plan(r)
        s.plan, s.plan_state = plan, "PLANNED"
        run = DagRun(plan=plan, run_task=self.runner_factory(s), fallback=fallback(s), incident_id=s.incident_id)
        s.run = run
        await run.run()
        s.plan_state = run.status
        if run.status == "AWAITING_APPROVAL":
            return [self._options_reply(s, run)]
        if run.halt_message:
            return [Reply(run.halt_message)]
        return [Reply(f"I couldn't complete the analysis ({'; '.join(run.errors.values()) or run.status}). "
                      "Please try again in a moment.")]

    def _options_reply(self, s: Session, run: DagRun) -> Reply:
        lines = [render.event_text(s.event), render.exposure_text(s.exposure)]
        if s.sourcing is not None:
            lines.append(f"Alternate suppliers found: {len(s.sourcing.alternates)}"
                         + (f" (degraded: {s.sourcing.notes})" if s.sourcing.degraded else ""))
        text = ("\n".join(lines) + "\n\n" + render.options_text(s.options)
                + "\n\nPick a plan in the card, or reply 'select OPT-C' and then 'approve'. "
                  "Nothing is sent until you approve.")
        payload = cards.options_carousel(s.options, s.incident_id, len(s.exposure.orders_at_risk))
        return Reply(text, "carousel", payload)

    def _status(self, s: Session) -> str:
        if s.run is None:
            return "No active incident yet. " + START_HINT
        return f"Incident {s.incident_id[:8]}: {s.run.status}." + (
            f" {len(s.receipt.results)} actions recorded." if s.receipt else "")

    # ---- card selections / typed commands ----------------------------------------------------
    async def _selection(self, s: Session, sel: dict) -> list[Reply]:
        oid = sel.get("option_id")
        if oid:
            if oid not in {o.option_id for o in s.options}:
                ids = ", ".join(o.option_id for o in s.options)
                return [Reply(f"I don't have {oid}. Available plans: {ids}.", "carousel",
                              cards.options_carousel(s.options, s.incident_id, len(s.exposure.orders_at_risk)))]
            s.chosen_option_id = oid
        opt = chosen_option(s)
        action = sel.get("action")
        log_task(log, f"selection action={action} option={opt.option_id}", incident_id=s.incident_id or "",
                 agent="orchestrator", status="audit")
        if action == "pick_option":
            text = (f"You picked {opt.option_id}: {opt.label}.\n"
                    f"Extra cost {render.inr(opt.cost_delta_inr)}, risk -{opt.risk_reduction:.0%}, "
                    f"{opt.orders_saved} orders saved. It will: {cards.action_summary(opt)}.\n"
                    "Approve in the card, or reply 'approve' / 'cancel'.")
            return [Reply(text, "review", cards.approval_review(opt, s.incident_id))]
        if action == "cancel":
            await s.run.resume(False)
            s.plan_state = s.run.status
            return [Reply("Cancelled. No emails were sent and nothing was changed. " + START_HINT)]
        if action == "approve":
            await s.run.resume(True)
            s.plan_state = s.run.status
            return self._receipt_replies(s, opt)
        return [Reply(HELP_TEXT)]

    def _receipt_replies(self, s: Session, opt) -> list[Reply]:
        run = s.run
        if s.receipt is None:
            err = "; ".join(run.errors.values()) or run.halt_message or run.status
            return [Reply(f"I could not execute the plan ({err}). Nothing was changed; you can approve again "
                          "after fixing the issue.")]
        rec = s.receipt
        n_sent = sum(r.status == "done" for r in rec.results)
        n_draft = sum(r.status == "draft" for r in rec.results)
        n_fail = sum(r.status == "failed" for r in rec.results)
        head = f"Executed {opt.option_id}: {n_sent} sent, {n_draft} drafted" + (f", {n_fail} failed" if n_fail else "")
        note = ("Demo mode: emails went to the demo inbox." if n_sent
                else "No emails were sent (email is not configured); drafts are ready to copy.")
        text = (f"{head}. ({note})\n{render.receipt_text(rec)}\n"
                f"Incident {s.incident_id[:8]} is closed. Ask 'update on the incident' any time.")
        self._persist(s, opt)
        return [Reply(text, "detail", cards.receipt_detail(rec), terminal=True)]

    def _persist(self, s: Session, opt) -> None:
        try:
            self.save_incident({"id": s.incident_id, "event": s.event.dict() if s.event else None,
                                "status": s.plan_state, "chosen_option": opt.dict(),
                                "outcome": f"{len(s.receipt.results)} actions"})
        except Exception as e:  # noqa: BLE001 - audit trail is best effort
            log_task(log, f"incident not saved: {e!r}", incident_id=s.incident_id, agent="orchestrator", status="warn")
