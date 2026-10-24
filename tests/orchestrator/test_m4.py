import asyncio
import json

import pytest

from agents.orchestrator import cards
from agents.orchestrator.cards import Reply, to_chat_message
from agents.orchestrator.handler import Orchestrator, parse_selection
from shared import dispatch

DEMO = "Cyclone warning on the Tamil Nadu coast, are we exposed?"


def run(c):
    return asyncio.run(c)


@pytest.fixture
def orch(monkeypatch, tmp_path):
    monkeypatch.setenv("DISPATCH_MODE", "mock")
    monkeypatch.setenv("PO_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("DEMO_SUPPLIER_INBOX", "demo@inbox.example")
    saved = []
    o = Orchestrator(save_incident=saved.append)
    o.saved = saved
    return o


def say(o, text, sender="u1"):
    return run(o.on_text(sender, text))


def sel(o, **kw):
    return say(o, json.dumps(kw))


def test_parse_selection_json_prose_and_typed():
    assert parse_selection('{"action": "approve", "option_id": "OPT-C"}')["action"] == "approve"
    assert parse_selection("The user picked option OPT-B")["option_id"] == "OPT-B"
    assert parse_selection("The user confirmed the plan")["action"] == "approve"
    assert parse_selection("select opt c") == {"option_id": "OPT-C", "action": "pick_option"}
    assert parse_selection("cancel")["action"] == "cancel"
    assert parse_selection("cyclone near chennai") == {}


def test_first_message_returns_text_plus_options_carousel(orch):
    (r,) = say(orch, DEMO)
    assert "₹1.82 Cr" in r.text and "OPT-C" in r.text and "approve" in r.text  # full text fallback
    assert r.kind == "carousel" and len(r.payload["items"]) == 3
    rec = [i for i in r.payload["items"] if "badges" in i]
    assert len(rec) == 1 and rec[0]["id"] == "OPT-C"
    sel_ = r.payload["items"][0]["primary_cta"]["selection"]
    assert sel_["action"] == "pick_option" and sel_["incident_id"]


def test_card_payloads_are_wire_valid(orch):
    (rep,) = say(orch, DEMO)
    raw = json.dumps(rep.payload)
    assert len(raw.encode()) < cards.MAX_PAYLOAD_BYTES
    msg = to_chat_message(rep)
    md = [c for c in msg.content if c.type == "metadata"][0].metadata
    assert md["card_protocol_version"] == "1" and md["requires_card_interaction"] == "true"
    assert md["card_kind"] == "carousel" and all(isinstance(v, str) for v in md.values())
    assert json.loads(md["card_payload"]) == rep.payload
    assert msg.content[0].text  # narration present
    # review + receipt payloads too
    (rev,) = say(orch, "select OPT-C")
    assert to_chat_message(rev).content[1].metadata["card_kind"] == "review"
    (rcp,) = say(orch, "approve")
    assert to_chat_message(rcp).content[1].metadata["is_terminal"] == "true"


def test_full_card_flow_pick_review_approve_receipt(orch):
    (r1,) = say(orch, DEMO)
    iid = r1.payload["items"][2]["primary_cta"]["selection"]["incident_id"]
    (r2,) = sel(orch, action="pick_option", option_id="OPT-C", incident_id=iid)
    assert r2.kind == "review" and "OPT-C" in r2.text
    assert r2.payload["approve_cta"]["selection"]["action"] == "approve"
    assert any(row["label"] == "Will do" for row in r2.payload["summary_rows"])
    (r3,) = sel(orch, action="approve", option_id="OPT-C", incident_id=iid)
    assert r3.kind == "detail" and r3.terminal and "Executed OPT-C" in r3.text
    assert len(r3.payload["summary_rows"]) >= 6 and r3.payload["ctas"]
    assert orch.saved and orch.saved[0]["id"] == iid and orch.saved[0]["chosen_option"]["option_id"] == "OPT-C"


def test_text_only_flow_works_without_cards(orch):
    say(orch, DEMO)
    (r2,) = say(orch, "select OPT-B")
    assert r2.kind == "review" and "OPT-B" in r2.text
    (r3,) = say(orch, "approve")
    assert "Executed OPT-B" in r3.text


def test_approve_without_picking_uses_recommended(orch):
    say(orch, DEMO)
    (r,) = say(orch, "approve")
    assert "Executed OPT-C" in r.text


def test_cancel_sends_nothing(orch):
    say(orch, DEMO)
    (r,) = say(orch, "cancel")
    assert "No emails were sent" in r.text and r.kind is None and not orch.saved
    (late,) = sel(orch, action="approve", option_id="OPT-C")  # stale button
    assert "no longer waiting" in late.text


def test_double_approve_executes_once(orch):
    say(orch, DEMO)
    say(orch, "approve")
    (again,) = sel(orch, action="approve", option_id="OPT-C")
    assert "no longer waiting" in again.text and len(orch.saved) == 1


def test_unknown_option_reshows_carousel(orch):
    say(orch, DEMO)
    (r,) = sel(orch, action="pick_option", option_id="OPT-Z")
    assert "don't have OPT-Z" in r.text and r.kind == "carousel"


def test_help_status_and_unsupported(orch):
    assert "SupplyShock online" in say(orch, "hello")[0].text
    assert "No active incident" in say(orch, "any update on the incident?")[0].text
    assert "not in this demo yet" in say(orch, "Is supplier S-07 safe right now?")[0].text


def test_scan_runs_the_full_flow(orch):
    (r,) = say(orch, "Are we exposed to anything right now?")
    assert r.kind == "carousel"


def test_unknown_place_becomes_a_question(orch, monkeypatch):
    from shared.models import TaskError
    real = dispatch.call

    async def bad(agent, request, timeout_s=20):
        if agent == "sentinel":
            return TaskError(incident_id=request.incident_id, task_id=request.task_id, code="INVALID_INPUT",
                             message="Could not find a place called 'Zzz'", retryable=False)
        return await real(agent, request, timeout_s)
    from agents.orchestrator.dispatcher import make_runner
    o = Orchestrator(runner_factory=lambda s: make_runner(s, bad), save_incident=lambda d: None)
    (r,) = say(o, "Cyclone near Chennai, are we exposed?")
    assert "Could not find a place called 'Zzz'" in r.text and "Which city" in r.text and r.kind is None


def test_internal_error_gives_a_safe_message(monkeypatch):
    def boom(s):
        raise RuntimeError("kaboom")
    o = Orchestrator(runner_factory=boom, save_incident=lambda d: None)
    (r,) = say(o, DEMO)
    assert "Something went wrong" in r.text and "kaboom" not in r.text


def test_sessions_are_per_sender(orch):
    say(orch, DEMO, sender="a")
    (rb,) = say(orch, "approve", sender="b")  # b never started anything: treated as a new, unknown request
    assert rb.kind is None and "SupplyShock online" in rb.text and not orch.saved
    (ra,) = say(orch, "approve", sender="a")
    assert "Executed OPT-C" in ra.text and len(orch.saved) == 1


def test_receipt_note_is_honest_about_email(orch, monkeypatch):
    monkeypatch.delenv("DEMO_SUPPLIER_INBOX")
    monkeypatch.setenv("DISPATCH_LOCAL_AGENTS", "action")  # real Action service, no email configured
    say(orch, DEMO)
    (r,) = say(orch, "approve")
    assert "0 sent" in r.text and "No emails were sent" in r.text and "went to the demo inbox" not in r.text


def test_picking_a_plan_never_executes_actions(monkeypatch, tmp_path):
    """Safety: only an explicit approve may reach the Action agent, even with ASI:One's @mention prefix."""
    from agents.orchestrator.dispatcher import make_runner
    monkeypatch.setenv("DISPATCH_MODE", "mock")
    calls = []
    real = dispatch.call

    async def spy(agent, request, timeout_s=20):
        calls.append(agent)
        return await real(agent, request, timeout_s)
    o = Orchestrator(runner_factory=lambda s: make_runner(s, spy), save_incident=lambda d: None)
    mention = "@agent1qgt7x0cakv0htfapv9yecj8mqw28jsyramh03aqztfquzlavcadc7nczfdz "
    say(o, mention + DEMO)
    assert "action" not in calls
    (r,) = say(o, mention + json.dumps({"action": "pick_option", "option_id": "OPT-C", "incident_id": "x"}))
    assert r.kind == "review" and "action" not in calls  # nothing executed yet
    (r2,) = say(o, mention + json.dumps({"action": "approve", "option_id": "OPT-C", "incident_id": "x"}))
    assert "Executed OPT-C" in r2.text and calls.count("action") == 1
