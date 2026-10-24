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
        "M-12 ECU housing: 6.0 days of cover < 9-day lead time of the best alternate -> CRITICAL.",
        "M-07 and M-15: cover below the 14-day disruption -> HIGH.",
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
        "score": 0.86,
    },
    {
        "supplier_id": "S-14",
        "name": "Coimbatore Alloys",
        "material_id": "M-12",
        "price_inr": 428.0,
        "lead_time_days": 7,
        "distance_km": 427.0,
        "score": 0.81,
    },
    {
        "supplier_id": "S-16",
        "name": "Pune Wiring Systems",
        "material_id": "M-07",
        "price_inr": 46.0,
        "lead_time_days": 6,
        "distance_km": 930.0,
        "score": 0.84,
    },
    {
        "supplier_id": "S-19",
        "name": "Ahmedabad Electronics Works",
        "material_id": "M-15",
        "price_inr": 1850.0,
        "lead_time_days": 10,
        "distance_km": 1372.0,
        "score": 0.78,
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

OPTIONS = [
    {
        "option_id": "OPT-A",
        "label": "Expedite current stock by air before landfall",
        "actions": [
            {"type": "expedite_email", "target_supplier_id": "S-03", "material_id": "M-12", "qty": 2500},
            {"type": "expedite_email", "target_supplier_id": "S-07", "material_id": "M-07", "qty": 6000},
            {"type": "expedite_email", "target_supplier_id": "S-07", "material_id": "M-15", "qty": 1200},
        ],
        "cost_delta_inr": 420_000.0,
        "risk_reduction": 0.55,
        "orders_saved": 7,
        "recommended": False,
        "rationale": "Fastest to act (about 2 days), but it depends on suppliers inside the "
        "cyclone zone shipping before landfall, so 5 of 12 orders stay at risk.",
    },
    {
        "option_id": "OPT-B",
        "label": "Switch M-12 to Pune Diecast (S-21)",
        "actions": [
            {"type": "rfq_email", "target_supplier_id": "S-21", "material_id": "M-12", "qty": 4000, "need_by": "2026-11-05"},
            {"type": "draft_po", "target_supplier_id": "S-21", "material_id": "M-12", "qty": 4000, "unit_price_inr": 412.5},
        ],
        "cost_delta_inr": 280_000.0,
        "risk_reduction": 0.80,
        "orders_saved": 11,
        "recommended": False,
        "rationale": "Cheapest option and removes the cyclone risk for M-12, but the 9-day "
        "lead time arrives after the 6-day stock-out, so 1 order still slips.",
    },
    {
        "option_id": "OPT-C",
        "label": "Split M-12 50/50 between S-03 and S-21, plus safety stock",
        "actions": [
            {"type": "expedite_email", "target_supplier_id": "S-03", "material_id": "M-12", "qty": 2000},
            {"type": "rfq_email", "target_supplier_id": "S-21", "material_id": "M-12", "qty": 2000, "need_by": "2026-11-05"},
            {"type": "rfq_email", "target_supplier_id": "S-14", "material_id": "M-12", "qty": 2000, "need_by": "2026-11-05"},
            {"type": "draft_po", "target_supplier_id": "S-21", "material_id": "M-12", "qty": 2000, "unit_price_inr": 412.5},
            {"type": "customer_notice", "order_id": "O-1007", "kind": "assurance", "new_date": None},
            {"type": "customer_notice", "order_id": "O-1014", "kind": "assurance", "new_date": None},
        ],
        "cost_delta_inr": 350_000.0,
        "risk_reduction": 0.90,
        "orders_saved": 12,
        "recommended": True,
        "rationale": "Saves all 12 orders for Rs 3.5 L extra: expedited stock covers the "
        "first days and S-21 covers the rest, with Coimbatore Alloys quoted as a backup.",
    },
]

STRATEGY_OPTIONS = {
    "incident_id": INCIDENT_ID,
    "task_id": "T5",
    "options": OPTIONS,
    "degraded": False,
    "notes": "",
}

RECOMMENDED = next(o for o in OPTIONS if o["recommended"])

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
        "results": [
            {"type": "expedite_email", "target": "S-03", "status": "done", "detail": "Expedite request sent to s03@supplyshock.demo (demo inbox)"},
            {"type": "rfq_email", "target": "S-21", "status": "done", "detail": "RFQ sent to s21@supplyshock.demo (demo inbox)"},
            {"type": "rfq_email", "target": "S-14", "status": "done", "detail": "RFQ sent to s14@supplyshock.demo (demo inbox)"},
            {"type": "draft_po", "target": "S-21", "status": "draft", "detail": "PO-2026-0412 generated: 2000 x M-12 @ Rs 412.50"},
            {"type": "customer_notice", "target": "O-1007", "status": "draft", "detail": "Assurance notice drafted for O-1007"},
            {"type": "customer_notice", "target": "O-1014", "status": "draft", "detail": "Assurance notice drafted for O-1014"},
        ],
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
