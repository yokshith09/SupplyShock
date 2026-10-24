"""Walk the supply graph: event -> suppliers -> materials -> products -> open orders. Owner: D2."""

from __future__ import annotations

from dataclasses import dataclass, field

from data import db
from shared.geo import DEFAULT_BUFFER, distance_km


@dataclass
class SupplierHit:
    supplier: dict
    distance_km: float


@dataclass
class Walk:
    zone_km: float
    hits: list[SupplierHit] = field(default_factory=list)
    nearest: SupplierHit | None = None
    # material_id -> list of hit supplier ids that are its primary source
    materials: dict[str, list[str]] = field(default_factory=dict)
    # material_id -> product ids using it
    products: dict[str, list[str]] = field(default_factory=dict)


def walk(center, radius_km: float, buffer: float = DEFAULT_BUFFER) -> Walk:
    zone = radius_km * buffer
    result = Walk(zone_km=zone)
    for supplier in db.list_suppliers():
        d = distance_km((supplier["lat"], supplier["lon"]), center)
        hit = SupplierHit(supplier, d)
        if result.nearest is None or d < result.nearest.distance_km:
            result.nearest = hit
        if d <= zone:
            result.hits.append(hit)
    result.hits.sort(key=lambda h: h.supplier["id"])

    for hit in result.hits:
        for material in db.materials_for_supplier(hit.supplier["id"], primary_only=True):
            result.materials.setdefault(material["id"], []).append(hit.supplier["id"])
    for material_id in result.materials:
        result.products[material_id] = [p["id"] for p in db.products_using_material(material_id)]
    return result


def fastest_alternate_lead(material_id: str, excluded: set[str]) -> int | None:
    """Shortest lead time among suppliers of the material outside the zone."""
    leads = [
        s["lead_time_days"]
        for s in db.suppliers_for_material(material_id)
        if s["id"] not in excluded
    ]
    return min(leads) if leads else None
