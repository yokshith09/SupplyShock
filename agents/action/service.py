"""Action service: carries out an APPROVED option. Pure logic, no uagents import.

handle(ActionRequest) -> ActionReceipt. One ActionResult per action, status in {done, failed, draft}.
Emails go only to DEMO_SUPPLIER_INBOX (see email_sender). Supplier/material/order lookups use data.db
(D2); if it is unavailable the id is used as the name so the flow still completes.
"""
import asyncio

from agents.action import email_sender, po_pdf, templates
from shared.logging import get_logger, log_task
from shared.models import ActionReceipt, ActionRequest, ActionResult, ServiceError

log = get_logger("action")


class Repo:
    """Thin wrapper over D2's data.db, tolerant of a missing database."""

    def _try(self, fn_name: str, key: str) -> dict | None:
        try:
            from data import db
            if not db.db_path().exists():  # never let sqlite create an empty DB as a side effect
                return None
            return getattr(db, fn_name)(key)
        except Exception:  # noqa: BLE001 - no DB on this branch/machine: fall back to ids
            return None

    def supplier(self, sid: str) -> dict:
        return self._try("get_supplier", sid) or {"id": sid, "name": sid, "email": None}

    def material(self, mid: str) -> dict:
        return self._try("get_material", mid) or {"id": mid, "name": mid, "unit": "pcs"}

    def order(self, oid: str) -> dict:
        return self._try("get_order", oid) or {"id": oid, "customer": "Valued customer"}


def _email(subject, body, supplier, transport) -> tuple[str, str]:
    r = email_sender.send(subject, body, supplier.get("email"), supplier.get("name", supplier.get("id", "?")),
                          transport=transport)
    if r.status == "done":
        return "done", r.detail
    # not sent (no config) or failed after retry: keep copy-ready text so nothing is lost
    return "draft", f"{r.detail}.\n--- copy-ready ---\nSubject: {subject}\n\n{body}"


def _do(a: dict, req: ActionRequest, repo: Repo, transport) -> ActionResult:
    t = a.get("type")
    if t in ("rfq_email", "expedite_email"):
        sup, mat = repo.supplier(a["target_supplier_id"]), repo.material(a["material_id"])
        qty, unit = int(a.get("qty", 0)), mat.get("unit", "pcs")
        subject, body = (templates.rfq(sup["name"], mat["name"], mat["id"], qty, unit, a.get("need_by"))
                         if t == "rfq_email" else
                         templates.expedite(sup["name"], mat["name"], mat["id"], qty, unit))
        status, detail = _email(subject, body, sup, transport)
        label = "RFQ" if t == "rfq_email" else "Expedite request"
        return ActionResult(type=t, target=a["target_supplier_id"], status=status,
                            detail=f"{label}: {detail}")
    if t == "draft_po":
        sup, mat = repo.supplier(a["target_supplier_id"]), repo.material(a["material_id"])
        qty, price = int(a.get("qty", 0)), float(a.get("unit_price_inr", 0))
        po, path = po_pdf.make_po(templates.COMPANY, sup, mat, qty, price, a.get("need_by"))
        return ActionResult(type=t, target=a["target_supplier_id"], status="draft",
                            detail=f"{po} generated: {qty} x {mat['id']} @ Rs {price:,.2f} -> {path}")
    if t == "customer_notice":
        order = repo.order(a["order_id"])
        subject, body = templates.customer_notice(order.get("customer", "Valued customer"), a["order_id"],
                                                  a.get("kind", "assurance"), a.get("new_date"))
        return ActionResult(type=t, target=a["order_id"], status="draft",
                            detail=f"{a.get('kind', 'assurance').capitalize()} notice drafted for "
                                   f"{a['order_id']}.\n--- copy-ready ---\nSubject: {subject}\n\n{body}")
    raise ValueError(f"unknown action type '{t}'")


async def handle(req: ActionRequest, repo: Repo | None = None, transport=None) -> ActionReceipt:
    if not (req.approved_by or "").strip():
        raise ServiceError("INVALID_INPUT", "actions can only run after explicit user approval", False)
    repo = repo or Repo()
    results: list[ActionResult] = []
    for a in req.option.actions:
        try:
            res = await asyncio.to_thread(_do, a, req, repo, transport)
        except Exception as e:  # noqa: BLE001 - one bad action must not stop the others
            res = ActionResult(type=str(a.get("type", "?")), target=str(a.get("target_supplier_id") or a.get("order_id") or "?"),
                               status="failed", detail=f"{e!r}")
        results.append(res)
        log_task(log, f"{res.type} -> {res.target}: {res.status}", incident_id=req.incident_id,
                 task_id=req.task_id, agent="action", status=res.status)
    _persist(req, results)
    failed = [r for r in results if r.status == "failed"]
    return ActionReceipt(incident_id=req.incident_id, task_id=req.task_id, results=results,
                         degraded=bool(failed),
                         notes=f"{len(failed)} of {len(results)} actions failed" if failed else "")


def _persist(req: ActionRequest, results: list[ActionResult]) -> None:
    try:
        from agents.orchestrator.store import Store
        st = Store()
        for r in results:
            st.log_action(req.incident_id, r.dict())
    except Exception as e:  # noqa: BLE001 - audit log is best effort
        log_task(log, f"actions_log not written: {e!r}", incident_id=req.incident_id, agent="action",
                 status="warn")
