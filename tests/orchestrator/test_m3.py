import asyncio
import json
import urllib.request

import pytest

from agents.action import email_sender
from agents.action.service import handle
from shared.models import ActionRequest, Option, ServiceError

ACTIONS = [
    {"type": "expedite_email", "target_supplier_id": "S-03", "material_id": "M-12", "qty": 2000},
    {"type": "rfq_email", "target_supplier_id": "S-21", "material_id": "M-12", "qty": 2000, "need_by": "2026-11-05"},
    {"type": "draft_po", "target_supplier_id": "S-21", "material_id": "M-12", "qty": 2000, "unit_price_inr": 412.5},
    {"type": "customer_notice", "order_id": "O-1007", "kind": "assurance", "new_date": None},
]


class FakeRepo:
    def supplier(self, sid):
        return {"id": sid, "name": f"Supplier {sid}", "email": f"{sid.lower()}@real-supplier.example",
                "city": "Pune", "country": "India"}

    def material(self, mid):
        return {"id": mid, "name": "ECU housing", "unit": "pcs"}

    def order(self, oid):
        return {"id": oid, "customer": "Mahindra Test"}


def req(actions=ACTIONS, approved_by="priya@apex"):
    return ActionRequest(incident_id="inc-1", task_id="T7", approved_by=approved_by,
                         option=Option(option_id="OPT-C", label="x", actions=actions))


def run(c):
    return asyncio.run(c)


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("DEMO_SUPPLIER_INBOX", "demo@inbox.example")
    monkeypatch.setenv("PO_OUTPUT_DIR", str(tmp_path / "po"))
    for k in ("RESEND_API_KEY", "SMTP_HOST", "SMTP_USER", "SMTP_PASS"):
        monkeypatch.delenv(k, raising=False)


def test_emails_only_go_to_demo_inbox_and_receipt_is_correct():
    sent = []
    r = run(handle(req(), FakeRepo(), transport=sent.append))
    assert [x.status for x in r.results] == ["done", "done", "draft", "draft"]
    assert len(sent) == 2
    for m in sent:
        assert m["To"] == "demo@inbox.example"
        assert "real-supplier.example" not in m["To"]
        assert "[DEMO" in m["Subject"]
    assert (r.incident_id, r.task_id, r.degraded) == ("inc-1", "T7", False)


def test_po_pdf_is_created_and_non_empty(tmp_path):
    r = run(handle(req([ACTIONS[2]]), FakeRepo(), transport=lambda m: None))
    pdfs = list((tmp_path / "po").glob("PO-*.pdf"))
    assert len(pdfs) == 1 and pdfs[0].stat().st_size > 500
    assert pdfs[0].read_bytes().startswith(b"%PDF") and pdfs[0].name.split(".")[0] in r.results[0].detail


def test_no_inbox_or_no_transport_means_draft_and_nothing_sent(monkeypatch):
    sent = []
    monkeypatch.delenv("DEMO_SUPPLIER_INBOX")
    r = run(handle(req([ACTIONS[1]]), FakeRepo(), transport=sent.append))
    assert r.results[0].status == "draft" and sent == []
    monkeypatch.setenv("DEMO_SUPPLIER_INBOX", "demo@inbox.example")
    r = run(handle(req([ACTIONS[1]]), FakeRepo()))  # no transport configured in env
    assert r.results[0].status == "draft" and "copy-ready" in r.results[0].detail


def test_email_failure_retries_once_then_becomes_draft(monkeypatch):
    monkeypatch.setattr(email_sender.time, "sleep", lambda s: None)
    calls = []

    def boom(m):
        calls.append(1)
        raise RuntimeError("smtp down")
    r = run(handle(req([ACTIONS[1]]), FakeRepo(), transport=boom))
    assert len(calls) == 2  # first try + one retry
    assert r.results[0].status == "draft" and "copy-ready" in r.results[0].detail and "smtp down" in r.results[0].detail


def test_requires_approval():
    with pytest.raises(ServiceError) as e:
        run(handle(req(approved_by=" "), FakeRepo(), transport=lambda m: None))
    assert e.value.code == "INVALID_INPUT"


def test_one_bad_action_does_not_stop_the_rest():
    acts = [{"type": "teleport"}] + ACTIONS[:1]
    r = run(handle(req(acts), FakeRepo(), transport=lambda m: None))
    assert [x.status for x in r.results] == ["failed", "done"] and r.degraded


def test_missing_database_falls_back_to_ids():
    r = run(handle(req([ACTIONS[1]]), None, transport=lambda m: None))  # real Repo, no DB on d1
    assert r.results[0].status == "done"


def test_resend_payload_and_user_agent(monkeypatch):
    seen = {}

    class Resp:
        def read(self):
            return b"{}"

    def fake_urlopen(req, timeout=0):
        seen["url"], seen["h"], seen["body"] = req.full_url, dict(req.header_items()), json.loads(req.data)
        return Resp()
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("RFQ_FROM_EMAIL", "onboarding@resend.dev")
    r = email_sender.send("Subj", "Body", "x@y.z", "Name")
    assert r.status == "done" and seen["url"] == "https://api.resend.com/emails"
    assert seen["body"]["to"] == ["demo@inbox.example"] and seen["body"]["from"] == "onboarding@resend.dev"
    assert seen["h"]["Authorization"] == "Bearer re_test" and "User-agent" in seen["h"]


def test_orchestrator_local_dispatch_reaches_action_service(monkeypatch):
    from shared import dispatch
    monkeypatch.setenv("DISPATCH_MODE", "mock")
    monkeypatch.setenv("DISPATCH_LOCAL_AGENTS", "action")
    r = run(dispatch.call("action", req()))
    assert len(r.results) == 4 and r.results[3].type == "customer_notice"
