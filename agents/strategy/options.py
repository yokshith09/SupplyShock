"""Build mitigation options A/B/C with deterministic numbers. Owner: D2.

Model (per CRITICAL/HIGH material, i.e. stock runs out during the disruption):
  cover    C  = days of stock on hand (from Exposure)
  extra    E  = days added by an expedited air shipment from the current supplier
  restart  R  = day new supply arrives (alternate lead time, or end of disruption)
An order is saved if, for every CRITICAL/HIGH material it needs, its due day d satisfies
d < C + E (still in stock) or d >= R (resupplied). Orders that only need MED/LOW materials
are safe in every option.

  OPT-A expedite:  E = EXPEDITE_SHARE of a week's capacity, R = disruption end, reliability 0.6
  OPT-B switch:    E = 0, R = best alternate's lead time,                    reliability 0.95
  OPT-C split:     E as in A, R as in B, half the alternate quantity,        reliability 0.9
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from datetime import date, timedelta

from data import db
from shared.models import Alternate, ExposureReport, MaterialExposure, Option, SourcingResult

EXPEDITE_SHARE = 0.25  # share of a week's capacity the in-zone supplier can air-ship before landfall
AIR_PREMIUM = 0.25  # air freight premium as a share of the goods' value
RELIABILITY = {"OPT-A": 0.6, "OPT-B": 0.95, "OPT-C": 0.9}
TIME_TO_EFFECT_EXPEDITE_DAYS = 2
RELEVANT = {"CRITICAL", "HIGH"}

DISRUPTION_DAYS_FALLBACK = 14


def today() -> date:
    pinned = os.getenv("SEED_TODAY")
    return date.fromisoformat(pinned) if pinned else date.today()


@dataclass
class MaterialPlan:
    exposure: MaterialExposure
    daily: float
    unit_cost: float
    primary_id: str
    primary_price: float
    expedite_qty: int
    alternates: list[Alternate]

    @property
    def expedite_days(self) -> float:
        return self.expedite_qty / self.daily if self.daily else 0.0

    @property
    def best(self) -> Alternate | None:
        return self.alternates[0] if self.alternates else None

    def gap_qty(self, disruption: int) -> int:
        """Quantity to buy elsewhere to cover the rest of the disruption (rounded up to 100)."""
        days = max(0.0, disruption - self.exposure.cover_days)
        return int(math.ceil(self.daily * days / 100.0) * 100)


@dataclass
class Draft:
    option_id: str
    label: str
    actions: list[dict] = field(default_factory=list)
    cost_delta_inr: float = 0.0
    saved_orders: list[str] = field(default_factory=list)
    lost_orders: list[str] = field(default_factory=list)
    saved_revenue_inr: float = 0.0
    time_to_effect_days: int = 0
    reliability: float = 1.0
    facts: list[str] = field(default_factory=list)


def _round100(qty: float) -> int:
    return int(math.ceil(qty / 100.0) * 100)


def material_plans(exposure: ExposureReport, sourcing: SourcingResult) -> list[MaterialPlan]:
    by_material: dict[str, list[Alternate]] = {}
    for alt in sourcing.alternates:
        by_material.setdefault(alt.material_id, []).append(alt)
    for alts in by_material.values():
        alts.sort(key=lambda a: -a.score)

    plans = []
    for m in exposure.materials:
        if m.severity not in RELEVANT:
            continue
        inv = db.inventory_for(m.material_id) or {"daily_consumption": 0}
        material = db.get_material(m.material_id) or {"unit_cost_inr": 0}
        suppliers = db.suppliers_for_material(m.material_id)
        primary = next((s for s in suppliers if s["id"] in m.supplier_ids), None) or (
            suppliers[0] if suppliers else {"id": m.supplier_ids[0] if m.supplier_ids else "", "price_inr": 0, "capacity_per_week": 0}
        )
        plans.append(
            MaterialPlan(
                exposure=m,
                daily=float(inv["daily_consumption"]),
                unit_cost=float(material["unit_cost_inr"]),
                primary_id=primary["id"],
                primary_price=float(primary.get("price_inr", 0)),
                expedite_qty=_round100(primary.get("capacity_per_week", 0) * EXPEDITE_SHARE),
                alternates=by_material.get(m.material_id, []),
            )
        )
    return plans


def _order_needs(order_ids: list[str], plans: list[MaterialPlan]) -> dict[str, tuple[dict, set[str]]]:
    """order_id -> (order row, relevant material ids it needs)."""
    products_for: dict[str, set[str]] = {
        p.exposure.material_id: {row["id"] for row in db.products_using_material(p.exposure.material_id)}
        for p in plans
    }
    needs = {}
    for oid in order_ids:
        order = db.get_order(oid)
        if not order:
            continue
        mats = {mid for mid, prods in products_for.items() if order["product_id"] in prods}
        needs[oid] = (order, mats)
    return needs


def _evaluate(draft: Draft, windows: dict[str, tuple[float, float]], needs, start: date) -> None:
    """windows: material_id -> (in_stock_until_day, restart_day)."""
    for oid, (order, mats) in needs.items():
        due_day = (date.fromisoformat(order["due_date"]) - start).days
        ok = all(due_day < windows[m][0] or due_day >= windows[m][1] for m in mats)
        (draft.saved_orders if ok else draft.lost_orders).append(oid)
        if ok:
            draft.saved_revenue_inr += float(order["value_inr"])


def _notices(draft: Draft, baseline_lost: set[str], windows, needs, start: date) -> list[dict]:
    notices = []
    for oid in draft.saved_orders:
        if oid in baseline_lost:
            notices.append({"type": "customer_notice", "order_id": oid, "kind": "assurance", "new_date": None})
    for oid in draft.lost_orders:
        _, mats = needs[oid]
        restart = max(windows[m][1] for m in mats)
        new_date = (start + timedelta(days=math.ceil(restart))).isoformat()
        notices.append({"type": "customer_notice", "order_id": oid, "kind": "delay", "new_date": new_date})
    return notices


def build_drafts(exposure: ExposureReport, sourcing: SourcingResult, disruption: int) -> list[Draft]:
    start = today()
    plans = material_plans(exposure, sourcing)
    if not plans:
        return []
    needs = _order_needs(exposure.orders_at_risk, plans)

    baseline = Draft("BASE", "No action")
    _evaluate(baseline, {p.exposure.material_id: (p.exposure.cover_days, disruption) for p in plans}, needs, start)
    baseline_lost = set(baseline.lost_orders)

    a = Draft("OPT-A", "Expedite current stock by air before landfall",
              time_to_effect_days=TIME_TO_EFFECT_EXPEDITE_DAYS, reliability=RELIABILITY["OPT-A"])
    b = Draft("OPT-B", "", reliability=RELIABILITY["OPT-B"])
    c = Draft("OPT-C", "", time_to_effect_days=TIME_TO_EFFECT_EXPEDITE_DAYS, reliability=RELIABILITY["OPT-C"])
    win_a, win_b, win_c = {}, {}, {}
    switched = []

    for p in plans:
        mid, cov = p.exposure.material_id, p.exposure.cover_days
        need_by = p.exposure.stockout_date
        expedite = {"type": "expedite_email", "target_supplier_id": p.primary_id, "material_id": mid, "qty": p.expedite_qty}

        # A: expedite only
        a.actions.append(dict(expedite))
        a.cost_delta_inr += p.expedite_qty * p.unit_cost * AIR_PREMIUM
        win_a[mid] = (cov + p.expedite_days, disruption)

        best = p.best
        if best is None:
            win_b[mid] = (cov, disruption)
            c.actions.append(dict(expedite))
            c.cost_delta_inr += p.expedite_qty * p.unit_cost * AIR_PREMIUM
            win_c[mid] = (cov + p.expedite_days, disruption)
            continue

        switched.append(f"{mid} to {best.supplier_id}")
        gap = p.gap_qty(disruption)
        diff = max(0.0, best.price_inr - p.primary_price)

        # B: switch the whole gap to the best alternate
        b.actions.append({"type": "rfq_email", "target_supplier_id": best.supplier_id, "material_id": mid, "qty": gap, "need_by": need_by})
        if p.exposure.severity == "CRITICAL":
            b.actions.append({"type": "draft_po", "target_supplier_id": best.supplier_id, "material_id": mid, "qty": gap, "unit_price_inr": best.price_inr})
        b.cost_delta_inr += gap * diff
        b.time_to_effect_days = max(b.time_to_effect_days, best.lead_time_days)
        win_b[mid] = (cov, best.lead_time_days)

        # C: expedite now + half the gap from the best alternate (+ backup quote)
        half = _round100(gap / 2)
        c.actions.append(dict(expedite))
        c.actions.append({"type": "rfq_email", "target_supplier_id": best.supplier_id, "material_id": mid, "qty": half, "need_by": need_by})
        if p.exposure.severity == "CRITICAL" and len(p.alternates) > 1:
            backup = p.alternates[1]
            c.actions.append({"type": "rfq_email", "target_supplier_id": backup.supplier_id, "material_id": mid, "qty": half, "need_by": need_by})
        if p.exposure.severity == "CRITICAL":
            c.actions.append({"type": "draft_po", "target_supplier_id": best.supplier_id, "material_id": mid, "qty": half, "unit_price_inr": best.price_inr})
        c.cost_delta_inr += p.expedite_qty * p.unit_cost * AIR_PREMIUM + half * diff
        win_c[mid] = (cov + p.expedite_days, best.lead_time_days)

    b.label = "Switch to backup suppliers: " + ", ".join(switched) if switched else "Switch to backup suppliers"
    c.label = "Split: expedite from current suppliers + order half from backups"
    if not switched:
        b.time_to_effect_days = disruption

    drafts = [a, b, c]
    for draft, windows in ((a, win_a), (b, win_b), (c, win_c)):
        _evaluate(draft, windows, needs, start)
        draft.actions += _notices(draft, baseline_lost, windows, needs, start)
        draft.cost_delta_inr = round(draft.cost_delta_inr, 0)
    return drafts


def to_option(d: Draft, revenue_at_risk: float, recommended: bool, rationale: str) -> Option:
    risk_reduction = d.reliability * (d.saved_revenue_inr / revenue_at_risk) if revenue_at_risk else 0.0
    return Option(
        option_id=d.option_id,
        label=d.label,
        actions=d.actions,
        cost_delta_inr=d.cost_delta_inr,
        risk_reduction=round(risk_reduction, 2),
        orders_saved=len(d.saved_orders),
        recommended=recommended,
        rationale=rationale,
    )
