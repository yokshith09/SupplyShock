"""Build the contract fixtures (one JSON per message model) from a single demo story.

Run:  python tests/fixtures/contracts/build_fixtures.py
Edit the story here, never the JSON files by hand, so all fixtures stay consistent.
Schemas: docs/TRD.md §5. Envelope rules: docs/04_TEAM_PLAN.md §E.1. Action shapes: §E.4.
"""

from __future__ import annotations

import json
from pathlib import Path

OUT_DIR = Path(__file__).parent

INCIDENT_ID = "7f3c2a9e-1b4d-4c8e-9a6f-2d5e8b1c0a47"

# Replay of Cyclone Michaung (Dec 2023), with dates shifted to the demo day.
EVENT = {
    "event_id": "GDACS-TC-1001046-replay",
    "type": "cyclone",
    "title": "Cyclone Michaung (replay of Dec 2023 event)",
    "center": {"lat": 13.08, "lon": 80.27},
    "radius_km": 150.0,
    "severity": "Orange",
    "start": "2026-10-24",
    "end": "2026-11-07",
    "sources": ["GDACS (replay)"],
    "confidence": 0.86,
}

MATERIALS = [
    {
        "material_id": "M-12",
        "name": "ECU housing (aluminium die-cast)",
        "supplier_ids": ["S-03"],
        "cover_days": 6.0,
        "stockout_date": "2026-10-30",
        "severity": "CRITICAL",
    },
    {
        "material_id": "M-07",
        "name": "Wiring harness connector",
        "supplier_ids": ["S-07"],
        "cover_days": 9.0,
        "stockout_date": "2026-11-02",
        "severity": "HIGH",
    },
    {
        "material_id": "M-15",
        "name": "ECU control PCB assembly",
        "supplier_ids": ["S-07"],
        "cover_days": 11.0,
        "stockout_date": "2026-11-04",
        "severity": "HIGH",
    },
    {
        "material_id": "M-04",
        "name": "Grey iron brake bracket casting",
        "supplier_ids": ["S-03"],
        "cover_days": 18.0,
        "stockout_date": "2026-11-11",
        "severity": "MED",
    },
    {
        "material_id": "M-22",
        "name": "Imported Hall-effect speed sensor (via Ennore port)",
        "supplier_ids": ["S-11"],
        "cover_days": 25.0,
        "stockout_date": "2026-11-18",
        "severity": "MED",
    },
]

ORDERS_AT_RISK = [
    "O-1003", "O-1005", "O-1007", "O-1008", "O-1011", "O-1014",
    "O-1016", "O-1019", "O-1022", "O-1025", "O-1028", "O-1031",
]  # fmt: skip

EXPOSURE_REPORT = {
    "incident_id": INCIDENT_ID,
    "task_id": "T2",
    "suppliers_hit": ["S-03", "S-07", "S-11"],
    "materials": MATERIALS,
    "orders_at_risk": ORDERS_AT_RISK,
    "revenue_at_risk_inr": 18_200_000.0,
    "trace": [
        "Impact zone: 150 km radius x 1.2 buffer = 180 km around (13.08, 80.27).",
        "S-03 Chennai Castings is 12 km from the cyclone centre -> inside the zone.",
        "S-07 Sriperumbudur Electronics is 38 km from the cyclone centre -> inside the zone.",
        "S-11 Ennore Port Forwarding is 15 km from the cyclone centre -> inside the zone.",
        "Expected disruption for an Orange cyclone: 14 days.",
        "M-12 ECU housing (aluminium die-cast): 6.0 days of cover < 7-day lead time of the fastest alternate -> CRITICAL.",
        "M-07 Wiring harness connector: 9.0 days of cover < 14-day disruption -> HIGH.",
        "M-15 ECU control PCB assembly: 11.0 days of cover < 14-day disruption -> HIGH.",
        "12 open orders use these 5 materials and are due within 14 days: Rs 1.82 Cr at risk.",
    ],
    "degraded": False,
    "notes": "",
}

ALTERNATES = [
    {
        "supplier_id": "S-21",
        "name": "Pune Diecast Pvt Ltd",
        "material_id": "M-12",
        "price_inr": 412.5,
        "lead_time_days": 9,
        "distance_km": 914.0,
        "score": 0.67,
    },
    {
        "supplier_id": "S-14",
        "name": "Coimbatore Alloys",
        "material_id": "M-12",
        "price_inr": 428.0,
        "lead_time_days": 7,
        "distance_km": 427.0,
        "score": 0.55,
    },
    {
        "supplier_id": "S-16",
        "name": "Pune Wiring Systems",
        "material_id": "M-07",
        "price_inr": 46.0,
        "lead_time_days": 6,
        "distance_km": 930.0,
        "score": 0.96,
    },
    {
        "supplier_id": "S-19",
        "name": "Ahmedabad Electronics Works",
        "material_id": "M-15",
        "price_inr": 1850.0,
        "lead_time_days": 10,
        "distance_km": 1372.0,
        "score": 0.95,
    },
]

SOURCING_RESULT = {
    "incident_id": INCIDENT_ID,
    "task_id": "T3",
    "alternates": ALTERNATES,
    "search_radius_km": 1500.0,
    "degraded": False,
    "notes": "",
}

OPTIONS = [{'option_id': 'OPT-A',
  'label': 'Expedite current stock by air before landfall',
  'actions': [{'type': 'expedite_email',
               'target_supplier_id': 'S-03',
               'material_id': 'M-12',
               'qty': 1800},
              {'type': 'expedite_email',
               'target_supplier_id': 'S-07',
               'material_id': 'M-07',
               'qty': 7500},
              {'type': 'expedite_email',
               'target_supplier_id': 'S-07',
               'material_id': 'M-15',
               'qty': 800},
              {'type': 'customer_notice',
               'order_id': 'O-1011',
               'kind': 'assurance',
               'new_date': None},
              {'type': 'customer_notice',
               'order_id': 'O-1022',
               'kind': 'assurance',
               'new_date': None},
              {'type': 'customer_notice',
               'order_id': 'O-1019',
               'kind': 'delay',
               'new_date': '2026-11-07'},
              {'type': 'customer_notice',
               'order_id': 'O-1028',
               'kind': 'delay',
               'new_date': '2026-11-07'}],
  'cost_delta_inr': 587875.0,
  'risk_reduction': 0.53,
  'orders_saved': 10,
  'recommended': False,
  'rationale': 'Fastest to act (about 2 days) for Rs 5.9 L extra, but it relies on suppliers '
               'inside the impact zone shipping before landfall; saves 10 of 12 orders.'},
 {'option_id': 'OPT-B',
  'label': 'Switch to backup suppliers: M-12 to S-21, M-07 to S-16, M-15 to S-19',
  'actions': [{'type': 'rfq_email',
               'target_supplier_id': 'S-21',
               'material_id': 'M-12',
               'qty': 8000,
               'need_by': '2026-10-30'},
              {'type': 'draft_po',
               'target_supplier_id': 'S-21',
               'material_id': 'M-12',
               'qty': 8000,
               'unit_price_inr': 412.5},
              {'type': 'rfq_email',
               'target_supplier_id': 'S-16',
               'material_id': 'M-07',
               'qty': 10000,
               'need_by': '2026-11-02'},
              {'type': 'rfq_email',
               'target_supplier_id': 'S-19',
               'material_id': 'M-15',
               'qty': 1500,
               'need_by': '2026-11-04'},
              {'type': 'customer_notice',
               'order_id': 'O-1019',
               'kind': 'assurance',
               'new_date': None},
              {'type': 'customer_notice',
               'order_id': 'O-1022',
               'kind': 'assurance',
               'new_date': None},
              {'type': 'customer_notice',
               'order_id': 'O-1028',
               'kind': 'assurance',
               'new_date': None},
              {'type': 'customer_notice',
               'order_id': 'O-1011',
               'kind': 'delay',
               'new_date': '2026-11-03'}],
  'cost_delta_inr': 535000.0,
  'risk_reduction': 0.86,
  'orders_saved': 11,
  'recommended': False,
  'rationale': 'Moves the at-risk materials to suppliers outside the zone for Rs 5.3 L extra; the '
               'first deliveries take up to 10 days, so it saves 11 of 12 orders.'},
 {'option_id': 'OPT-C',
  'label': 'Split: expedite from current suppliers + order half from backups',
  'actions': [{'type': 'expedite_email',
               'target_supplier_id': 'S-03',
               'material_id': 'M-12',
               'qty': 1800},
              {'type': 'rfq_email',
               'target_supplier_id': 'S-21',
               'material_id': 'M-12',
               'qty': 4000,
               'need_by': '2026-10-30'},
              {'type': 'rfq_email',
               'target_supplier_id': 'S-14',
               'material_id': 'M-12',
               'qty': 4000,
               'need_by': '2026-10-30'},
              {'type': 'draft_po',
               'target_supplier_id': 'S-21',
               'material_id': 'M-12',
               'qty': 4000,
               'unit_price_inr': 412.5},
              {'type': 'expedite_email',
               'target_supplier_id': 'S-07',
               'material_id': 'M-07',
               'qty': 7500},
              {'type': 'rfq_email',
               'target_supplier_id': 'S-16',
               'material_id': 'M-07',
               'qty': 5000,
               'need_by': '2026-11-02'},
              {'type': 'expedite_email',
               'target_supplier_id': 'S-07',
               'material_id': 'M-15',
               'qty': 800},
              {'type': 'rfq_email',
               'target_supplier_id': 'S-19',
               'material_id': 'M-15',
               'qty': 800,
               'need_by': '2026-11-04'},
              {'type': 'customer_notice',
               'order_id': 'O-1011',
               'kind': 'assurance',
               'new_date': None},
              {'type': 'customer_notice',
               'order_id': 'O-1019',
               'kind': 'assurance',
               'new_date': None},
              {'type': 'customer_notice',
               'order_id': 'O-1022',
               'kind': 'assurance',
               'new_date': None},
              {'type': 'customer_notice',
               'order_id': 'O-1028',
               'kind': 'assurance',
               'new_date': None}],
  'cost_delta_inr': 862875.0,
  'risk_reduction': 0.9,
  'orders_saved': 12,
  'recommended': True,
  'rationale': 'Expedited stock bridges the first days and backup suppliers cover the rest, saving '
               '12 of 12 orders for Rs 8.6 L extra.'}]

STRATEGY_OPTIONS = {
    "incident_id": INCIDENT_ID,
    "task_id": "T5",
    "options": OPTIONS,
    "degraded": False,
    "notes": "",
}

RECOMMENDED = next(o for o in OPTIONS if o["recommended"])


def _receipt_line(action: dict) -> dict:
    kind = action["type"]
    if kind == "customer_notice":
        word = "Assurance" if action["kind"] == "assurance" else "Delay"
        return {"type": kind, "target": action["order_id"], "status": "draft",
                "detail": f"{word} notice drafted for {action['order_id']}"}
    target = action["target_supplier_id"]
    email = f"{target.lower().replace('-', '')}@supplyshock.demo"
    if kind == "draft_po":
        return {"type": kind, "target": target, "status": "draft",
                "detail": f"PO-2026-0412 generated: {action['qty']} x {action['material_id']} @ Rs {action['unit_price_inr']:,.2f}"}
    word = "RFQ" if kind == "rfq_email" else "Expedite request"
    return {"type": kind, "target": target, "status": "done", "detail": f"{word} sent to {email} (demo inbox)"}


FIXTURES: dict[str, dict] = {
    "EventQuery": {
        "incident_id": INCIDENT_ID,
        "task_id": "T1",
        "location": "Tamil Nadu coast",
        "type": "cyclone",
        "horizon_days": 7,
    },
    "EventResult": {
        "incident_id": INCIDENT_ID,
        "task_id": "T1",
        "events": [EVENT],
        "degraded": False,
        "notes": "",
    },
    "ExposureRequest": {"incident_id": INCIDENT_ID, "task_id": "T2", "event": EVENT},
    "ExposureReport": EXPOSURE_REPORT,
    "SourcingRequest": {
        "incident_id": INCIDENT_ID,
        "task_id": "T3",
        "material_ids": ["M-12", "M-07", "M-15"],
        "exclude_zone": EVENT,
    },
    "SourcingResult": SOURCING_RESULT,
    "StrategyRequest": {
        "incident_id": INCIDENT_ID,
        "task_id": "T5",
        "exposure": EXPOSURE_REPORT,
        "sourcing": SOURCING_RESULT,
    },
    "StrategyOptions": STRATEGY_OPTIONS,
    "ActionRequest": {
        "incident_id": INCIDENT_ID,
        "task_id": "T7",
        "option": RECOMMENDED,
        "approved_by": "user:asi1-demo",
    },
    "ActionReceipt": {
        "incident_id": INCIDENT_ID,
        "task_id": "T7",
        "results": [_receipt_line(a) for a in RECOMMENDED["actions"]],
        "degraded": False,
        "notes": "",
    },
    "WatchSubscribe": {
        "incident_id": INCIDENT_ID,
        "task_id": "T8",
        "event": EVENT,
        "user_sender": "agent1qdemouseraddressplaceholder000000000000000000000000",
        "interval_min": 30,
    },
    "WatchAlert": {
        "incident_id": INCIDENT_ID,
        "change": "Cyclone downgraded from Orange to Green; track moved 40 km north of Chennai.",
        "new_severity": "Green",
    },
    "TaskError": {
        "incident_id": INCIDENT_ID,
        "task_id": "T3",
        "code": "UPSTREAM_API",
        "message": "Frankfurter FX API returned HTTP 503 after 2 retries.",
        "retryable": True,
    },
}


def main() -> None:
    for name, payload in FIXTURES.items():
        path = OUT_DIR / f"{name}.json"
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
        )
    print(f"Wrote {len(FIXTURES)} fixtures to {OUT_DIR}")


if __name__ == "__main__":
    main()
