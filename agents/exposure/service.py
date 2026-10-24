"""Exposure: which suppliers, materials and orders an event puts at risk. Owner: D2.

    async def handle(req: ExposureRequest) -> ExposureReport

Deterministic (no LLM): uses data/db.py and shared/geo.py only. See docs/TRD.md §10.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import timedelta

from agents.exposure import cover
from agents.exposure.graph import fastest_alternate_lead, walk
from data import db
from shared.constants import ErrorCode
from shared.models import ExposureReport, ExposureRequest, MaterialExposure, ServiceError

logger = logging.getLogger("supplyshock.exposure")


def inr_short(amount: float) -> str:
    """Rs amount in crore / lakh, e.g. 'Rs 1.82 Cr', 'Rs 4.2 L'."""
    if amount >= 1e7:
        return f"Rs {amount / 1e7:.2f} Cr"
    if amount >= 1e5:
        return f"Rs {amount / 1e5:.1f} L"
    return f"Rs {amount:,.0f}"


def _compute(req: ExposureRequest) -> ExposureReport:
    event = req.event
    start = cover.today()
    graph = walk(event.center, event.radius_km)
    trace = [
        f"Impact zone: {event.radius_km:.0f} km radius x 1.2 buffer = {graph.zone_km:.0f} km "
        f"around ({event.center.lat:.2f}, {event.center.lon:.2f})."
    ]

    if not graph.hits:
        if graph.nearest:
            s = graph.nearest.supplier
            trace.append(
                f"No suppliers inside the zone. Closest is {s['id']} {s['name']} "
                f"({s['city']}), {graph.nearest.distance_km:.0f} km from the {event.type} centre."
            )
        return ExposureReport(incident_id=req.incident_id, task_id=req.task_id, trace=trace)

    for hit in graph.hits:
        s = hit.supplier
        trace.append(
            f"{s['id']} {s['name']} is {hit.distance_km:.0f} km from the {event.type} centre "
            "-> inside the zone."
        )

    days = cover.disruption_days(event.type, event.severity)
    trace.append(f"Expected disruption for an {event.severity} {event.type}: {days} days.")

    hit_ids = {h.supplier["id"] for h in graph.hits}
    materials: list[MaterialExposure] = []
    for material_id, supplier_ids in graph.materials.items():
        material = db.get_material(material_id) or {"name": material_id}
        inv = db.inventory_for(material_id)
        cov = cover.cover_days(inv["on_hand_qty"], inv["daily_consumption"]) if inv else 0.0
        alt_lead = fastest_alternate_lead(material_id, hit_ids)
        sev = cover.severity(cov, days, alt_lead)
        materials.append(
            MaterialExposure(
                material_id=material_id,
                name=material["name"],
                supplier_ids=sorted(supplier_ids),
                cover_days=cov,
                stockout_date=cover.stockout_date(cov, start),
                severity=sev,
            )
        )
        if sev == "CRITICAL":
            reason = (
                f"< {alt_lead}-day lead time of the fastest alternate"
                if alt_lead is not None
                else f"< {days}-day disruption and no alternate supplier"
            )
            trace.append(f"{material_id} {material['name']}: {cov} days of cover {reason} -> CRITICAL.")
        elif sev == "HIGH":
            trace.append(
                f"{material_id} {material['name']}: {cov} days of cover < {days}-day disruption -> HIGH."
            )

    materials.sort(key=lambda m: (cover.SEVERITY_RANK[m.severity], m.cover_days))

    product_ids = sorted({p for ps in graph.products.values() for p in ps})
    cutoff = (start + timedelta(days=days)).isoformat()
    orders = [o for o in db.open_orders_for_products(product_ids) if o["due_date"] < cutoff]
    revenue = float(sum(o["value_inr"] for o in orders))
    trace.append(
        f"{len(orders)} open orders use these {len(materials)} materials and are due within "
        f"{days} days: {inr_short(revenue)} at risk."
    )

    return ExposureReport(
        incident_id=req.incident_id,
        task_id=req.task_id,
        suppliers_hit=sorted(hit_ids),
        materials=materials,
        orders_at_risk=[o["id"] for o in orders],
        revenue_at_risk_inr=revenue,
        trace=trace,
    )


async def handle(req: ExposureRequest) -> ExposureReport:
    started = time.perf_counter()
    if not db.db_path().exists():
        raise ServiceError(
            ErrorCode.INTERNAL.value,
            "ERP data is not loaded. Run `python data/seed_generator.py` first.",
            retryable=False,
        )
    try:
        report = _compute(req)
    except sqlite3.Error as exc:
        logger.exception("exposure db error")
        raise ServiceError(ErrorCode.INTERNAL.value, f"ERP database error: {exc}", retryable=True) from exc

    logger.info(
        "exposure done",
        extra={
            "incident_id": req.incident_id,
            "task_id": req.task_id,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "suppliers_hit": len(report.suppliers_hit),
        },
    )
    return report
