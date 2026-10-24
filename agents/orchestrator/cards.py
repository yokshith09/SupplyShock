"""ASI:One Interactive Cards (docs: innovationlab.fetch.ai/resources/docs/interactive-cards).

A card is a normal ChatMessage: one TextContent (narration, always shown, also the fallback) plus one
MetadataContent with card_protocol_version / requires_card_interaction / card_kind / card_payload (JSON string).
Invalid cards are silently shown as plain text by ASI:One, so every Reply carries complete text.
Builders take response models (never raw dicts) and return plain dict payloads.
"""
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from agents.orchestrator.render import inr
from shared.models import ActionReceipt, Option

MAX_PAYLOAD_BYTES = 64 * 1024


@dataclass
class Reply:
    text: str
    kind: str | None = None  # carousel | detail | form | review | custom
    payload: dict | None = None
    terminal: bool = False


def _image() -> dict:
    url = os.getenv("CARD_IMAGE_URL", "").strip()
    return {"image": url} if url else {}


def action_summary(option: Option) -> str:
    labels = {"rfq_email": "RFQ email", "expedite_email": "expedite request", "draft_po": "draft PO",
              "customer_notice": "customer notice"}
    counts: dict[str, int] = {}
    for a in option.actions:
        counts[a.get("type", "?")] = counts.get(a.get("type", "?"), 0) + 1
    parts = [f"{n} {labels.get(t, t)}{'s' if n > 1 else ''}" for t, n in counts.items()]
    return ", ".join(parts) or "no actions"


def options_carousel(options: list[Option], incident_id: str, total_orders: int | None = None) -> dict:
    items = []
    for o in options:
        saved = f"saves {o.orders_saved}" + (f"/{total_orders} orders" if total_orders else " orders")
        items.append({
            "id": o.option_id,
            "title": f"{o.option_id}: {o.label}"[:90],
            "subtitle": f"Cost +{inr(o.cost_delta_inr)} · risk -{o.risk_reduction:.0%} · {saved}",
            "secondary_text": inr(o.cost_delta_inr),
            **({"badges": [{"label": "Recommended", "variant": "success"}]} if o.recommended else {}),
            **_image(),
            "primary_cta": {"label": "Select", "selection": {
                "action": "pick_option", "option_id": o.option_id, "incident_id": incident_id}},
        })
    return {"title": "Choose a response plan", "subtitle": "Scored on cost, risk and orders saved", "items": items}


def approval_review(option: Option, incident_id: str) -> dict:
    rows = [
        {"label": "Plan", "value": f"{option.option_id}: {option.label}"},
        {"label": "Extra cost", "value": inr(option.cost_delta_inr)},
        {"label": "Risk reduction", "value": f"{option.risk_reduction:.0%}"},
        {"label": "Orders saved", "value": str(option.orders_saved)},
        {"label": "Will do", "value": action_summary(option)},
        {"label": "Demo mode", "value": "Emails go to a controlled demo inbox, not real suppliers"},
    ]
    if option.rationale:
        rows.append({"label": "Why", "value": option.rationale})
    return {
        "title": "Approve this plan?",
        "summary_rows": rows,
        "approve_cta": {"label": "Approve and execute", "primary": True,
                        "selection": {"action": "approve", "option_id": option.option_id, "incident_id": incident_id}},
        "reject_cta": {"label": "Cancel", "selection": {"action": "cancel", "incident_id": incident_id}},
    }


def receipt_detail(receipt: ActionReceipt) -> dict:
    status = {"done": "SENT", "draft": "DRAFT", "failed": "FAILED"}
    return {
        "title": "Execution receipt",
        "summary_rows": [{"label": f"{r.type.replace('_', ' ')} → {r.target}",
                          "value": status.get(r.status, r.status.upper())} for r in receipt.results]
        or [{"label": "Actions", "value": "none"}],
        "ctas": [{"label": "Done", "primary": True, "selection": {"action": "done"}}],
    }


def to_chat_message(reply: Reply):
    """Convert a Reply to a uagents ChatMessage (imported lazily so cards.py stays unit-testable)."""
    from uagents_core.contrib.protocols.chat import ChatMessage, MetadataContent, TextContent
    content = [TextContent(type="text", text=reply.text or "(no content)")]
    if reply.kind and reply.payload:
        raw = json.dumps(reply.payload, ensure_ascii=False)
        if len(raw.encode()) <= MAX_PAYLOAD_BYTES:
            md = {"card_protocol_version": "1", "requires_card_interaction": "true",
                  "card_kind": reply.kind, "card_payload": raw, "preferred_drawer_width_px": "540"}
            if reply.terminal:
                md["is_terminal"] = "true"
            content.append(MetadataContent(type="metadata", metadata=md))
    return ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(), content=content)
