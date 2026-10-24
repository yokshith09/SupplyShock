"""Sourcing: find and rank alternate suppliers outside the event zone. Owner: D2.

    async def handle(req: SourcingRequest) -> SourcingResult

For each material: candidates = its suppliers outside exclude_zone (radius x 1.2). The search
widens step by step: within 1,500 km of the event, then the same country as the material's
current primary supplier, then worldwide. Top 3 per material, in request order.
search_radius_km = 1500 if everything was found nearby, 0 if any material needed a worldwide
search (national-only widening is reported in notes). All prices are already INR in the ERP data.
"""

from __future__ import annotations

import logging
import sqlite3
import time

from agents.sourcing.ranker import rank
from data import db
from shared.constants import ErrorCode
from shared.geo import distance_km, within_radius
from shared.models import Alternate, ServiceError, SourcingRequest, SourcingResult

logger = logging.getLogger("supplyshock.sourcing")

NEARBY_KM = 1500.0
GLOBAL = 0.0


def _primary_country(suppliers: list[dict]) -> str | None:
    primary = next((s for s in suppliers if s["is_primary"]), None)
    return primary["country"] if primary else None


def _alternates_for(material_id: str, req: SourcingRequest) -> tuple[list[Alternate], str, str | None]:
    """(alternates, stage, note). stage is 'nearby' | 'national' | 'global' | 'none'."""
    zone = req.exclude_zone
    suppliers = db.suppliers_for_material(material_id)
    outside = []
    for s in suppliers:
        point = (s["lat"], s["lon"])
        if within_radius(point, zone.center, zone.radius_km):
            continue
        outside.append({**s, "distance_km": round(distance_km(point, zone.center), 0)})

    if not suppliers:
        return [], "none", f"{material_id}: unknown material or no suppliers on record."
    if not outside:
        return [], "none", f"{material_id}: every known supplier is inside the impact zone."

    country = _primary_country(suppliers)
    stages = [
        ("nearby", [c for c in outside if c["distance_km"] <= NEARBY_KM]),
        ("national", [c for c in outside if country and c["country"] == country]),
        ("global", outside),
    ]
    stage, pool = next((name, pool) for name, pool in stages if pool)

    note = None
    if stage == "national":
        note = f"{material_id}: nothing within {NEARBY_KM:.0f} km, widened to suppliers in {country}."
    elif stage == "global":
        note = f"{material_id}: nothing within {NEARBY_KM:.0f} km or in {country}, searched worldwide."

    alternates = [
        Alternate(
            supplier_id=c["id"],
            name=c["name"],
            material_id=material_id,
            price_inr=float(c["price_inr"]),
            lead_time_days=int(c["lead_time_days"]),
            distance_km=float(c["distance_km"]),
            score=s,
        )
        for c, s in rank(pool)
    ]
    return alternates, stage, note


def _compute(req: SourcingRequest) -> SourcingResult:
    alternates: list[Alternate] = []
    notes: list[str] = []
    widest = "nearby"
    for material_id in dict.fromkeys(req.material_ids):  # keep order, drop duplicates
        found, stage, note = _alternates_for(material_id, req)
        alternates += found
        if note:
            notes.append(note)
        if stage == "global":
            widest = "global"
    return SourcingResult(
        incident_id=req.incident_id,
        task_id=req.task_id,
        alternates=alternates,
        search_radius_km=GLOBAL if widest == "global" else NEARBY_KM,
        notes=" ".join(notes),
    )


async def handle(req: SourcingRequest) -> SourcingResult:
    started = time.perf_counter()
    if not db.db_path().exists():
        raise ServiceError(
            ErrorCode.INTERNAL.value,
            "ERP data is not loaded. Run `python data/seed_generator.py` first.",
            retryable=False,
        )
    try:
        result = _compute(req)
    except sqlite3.Error as exc:
        logger.exception("sourcing db error")
        raise ServiceError(ErrorCode.INTERNAL.value, f"ERP database error: {exc}", retryable=True) from exc

    logger.info(
        "sourcing done",
        extra={
            "incident_id": req.incident_id,
            "task_id": req.task_id,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "alternates": len(result.alternates),
        },
    )
    return result
