"""Standalone chat behaviour for D2's agents in ASI:One (when used without the Orchestrator). Owner: D2."""

from __future__ import annotations

import re
from uuid import uuid4

from agents.exposure import service as exposure_service
from agents.sentinel import service as sentinel_service
from agents.sentinel.geocode import GeocodeUnavailable, geocode
from agents.sourcing import service as sourcing_service
from agents.strategy import service as strategy_service
from data import db
from shared.models import (
    Event,
    EventQuery,
    ExposureReport,
    ExposureRequest,
    ServiceError,
    SourcingRequest,
    SourcingResult,
    StrategyRequest,
)

EVENT_WORDS = {
    "cyclone": "cyclone", "storm": "cyclone", "typhoon": "cyclone", "hurricane": "cyclone",
    "flood": "flood", "earthquake": "earthquake", "quake": "earthquake", "wildfire": "wildfire",
    "strike": "strike", "port closure": "port_closure", "fire": "fire",
}
FILLER = re.compile(
    r"\b(any|are|is|there|we|our|us|exposed|exposure|events?|disruptions?|risk|what|if|a|an|the|"
    r"near|in|at|around|on|coast(al)?|warning|alert|backups?|alternates?|suppliers?|for|options?|"
    r"show|me|find|of|to|hit|hits|happens|please)\b|[?!.,]",
    re.IGNORECASE,
)
MATERIAL_RE = re.compile(r"\bM-\d{2}\b", re.IGNORECASE)
WHAT_IF_RADIUS_KM = 150.0


def event_type(text: str) -> str | None:
    lowered = text.lower()
    return next((v for k, v in EVENT_WORDS.items() if k in lowered), None)


def place_from(text: str) -> str | None:
    cleaned = MATERIAL_RE.sub(" ", text)
    for word in EVENT_WORDS:
        cleaned = re.sub(rf"\b{word}\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = " ".join(FILLER.sub(" ", cleaned).split())
    return cleaned or None


def new_id() -> str:
    return str(uuid4())


async def find_event(text: str) -> tuple[Event | None, str]:
    """A live/replay event near the place in the text, else a what-if event there."""
    place, etype = place_from(text), event_type(text)
    if not place:
        return None, "Tell me a place, for example: 'cyclone near Chennai'."
    result = await sentinel_service.handle(EventQuery(incident_id=new_id(), task_id="chat", location=place, type=etype))
    if result.events:
        e = result.events[0]
        return e, f"Event: {e.title} ({e.type}, {e.severity}, {e.radius_km:.0f} km radius, confidence {e.confidence:.2f})."
    try:
        point = await geocode(place)
    except GeocodeUnavailable:
        point = None
    if not point:
        return None, f"I couldn't find '{place}'. Try a city or state name."
    e = Event(
        event_id=f"what-if-{place.lower().replace(' ', '-')}",
        type=etype or "cyclone",
        title=f"What-if: {etype or 'cyclone'} near {place.title()}",
        center={"lat": point[0], "lon": point[1]},
        radius_km=WHAT_IF_RADIUS_KM,
        severity="Orange",
        start="",
        sources=["what-if"],
        confidence=0.0,
    )
    return e, f"No active event found near {place.title()}, so this is a what-if for a {e.type} with a {WHAT_IF_RADIUS_KM:.0f} km radius."


def inr(amount: float) -> str:
    return exposure_service.inr_short(amount).replace("Rs ", "₹")


def exposure_text(rep: ExposureReport) -> str:
    if not rep.suppliers_hit:
        return "None of your suppliers are inside the impact zone. " + (rep.trace[-1] if rep.trace else "")
    lines = [
        f"{len(rep.suppliers_hit)} suppliers hit ({', '.join(rep.suppliers_hit)}), {len(rep.materials)} materials, "
        f"{len(rep.orders_at_risk)} orders and {inr(rep.revenue_at_risk_inr)} of revenue at risk."
    ]
    for m in rep.materials[:5]:
        lines.append(f"- {m.material_id} {m.name}: {m.cover_days:g} days of stock, stock-out {m.stockout_date}, {m.severity}")
    return "\n".join(lines)


def sourcing_text(res: SourcingResult) -> str:
    if not res.alternates:
        return "No backup suppliers found. " + res.notes
    lines = [
        f"- {a.material_id}: {a.supplier_id} {a.name}, ₹{a.price_inr:,.2f}, {a.lead_time_days} days, "
        f"{a.distance_km:,.0f} km (score {a.score:.2f})"
        for a in res.alternates
    ]
    if res.notes:
        lines.append(res.notes)
    return "\n".join(lines)


async def sentinel_chat(text: str) -> str:
    place, etype = place_from(text), event_type(text)
    res = await sentinel_service.handle(EventQuery(incident_id=new_id(), task_id="chat", location=place, type=etype))
    where = f" near {place.title()}" if place else ""
    if not res.events:
        return f"No active disruption events found{where}. {res.notes}".strip()
    lines = [f"{len(res.events)} disruption event(s){where}:"]
    for e in res.events[:5]:
        lines.append(
            f"- {e.title}: {e.type}, {e.severity}, {e.radius_km:.0f} km radius, "
            f"confidence {e.confidence:.2f} (sources: {', '.join(e.sources)})"
        )
    if res.notes:
        lines.append(res.notes)
    return "\n".join(lines)


async def _exposure_for(text: str) -> tuple[Event | None, ExposureReport | None, str]:
    event, intro = await find_event(text)
    if event is None:
        return None, None, intro
    rep = await exposure_service.handle(ExposureRequest(incident_id=new_id(), task_id="chat", event=event))
    return event, rep, intro


async def exposure_chat(text: str) -> str:
    _, rep, intro = await _exposure_for(text)
    return intro if rep is None else f"{intro}\n{exposure_text(rep)}"


def _materials_in(text: str) -> list[str]:
    ids = [m.upper() for m in MATERIAL_RE.findall(text)]
    if ids:
        return ids
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    with db.get_connection() as conn:
        rows = conn.execute("SELECT id, name FROM materials").fetchall()
    overlap = {
        r["id"]: len(words & {w for w in re.findall(r"[a-z0-9]+", r["name"].lower()) if len(w) > 2})
        for r in rows
    }
    best = max(overlap.values(), default=0)
    return [mid for mid, n in overlap.items() if n == best][:3] if best else []


def _around_current_supplier(material_id: str) -> Event:
    """Zone around the material's current primary supplier: excludes it, measures from it."""
    suppliers = db.suppliers_for_material(material_id)
    primary = next((s for s in suppliers if s["is_primary"]), suppliers[0] if suppliers else None)
    center = {"lat": primary["lat"], "lon": primary["lon"]} if primary else {"lat": 0.0, "lon": 0.0}
    return Event(event_id="current-supplier", type="other", title="current supplier", center=center,
                 radius_km=1.0, severity="Green", start="")


async def sourcing_chat(text: str) -> str:
    materials = _materials_in(text)
    event, intro = None, ""
    if place_from(text):
        try:
            event, intro = await find_event(text)
        except ServiceError:
            if not materials:  # words were neither a material nor a place
                raise
        if event is None and materials:
            intro = ""  # material-only question: search everywhere
    if not materials and event is not None:
        rep = await exposure_service.handle(ExposureRequest(incident_id=new_id(), task_id="chat", event=event))
        materials = [m.material_id for m in rep.materials]
    if not materials:
        return "Tell me a material and a place, for example: 'backup for M-12 near Chennai'."
    if event is not None:
        res = await sourcing_service.handle(
            SourcingRequest(incident_id=new_id(), task_id="chat", material_ids=materials, exclude_zone=event)
        )
        return "\n".join(x for x in (intro, sourcing_text(res)) if x)

    # No place: alternates to each material's current supplier (distances measured from it).
    parts = ["Backups to your current suppliers (distance from the current supplier):"]
    for mid in materials:
        res = await sourcing_service.handle(
            SourcingRequest(incident_id=new_id(), task_id="chat", material_ids=[mid],
                            exclude_zone=_around_current_supplier(mid))
        )
        parts.append(sourcing_text(res.copy(update={"notes": ""})))
    return "\n".join(parts)


async def strategy_chat(text: str) -> str:
    event, rep, intro = await _exposure_for(text)
    if rep is None:
        return intro
    if not rep.orders_at_risk:
        return f"{intro}\n{exposure_text(rep)}"
    src = await sourcing_service.handle(
        SourcingRequest(incident_id=rep.incident_id, task_id="chat", exclude_zone=event,
                        material_ids=[m.material_id for m in rep.materials])
    )
    res = await strategy_service.handle(
        StrategyRequest(incident_id=rep.incident_id, task_id="chat", exposure=rep, sourcing=src)
    )
    lines = [intro, exposure_text(rep), "Options:"]
    for o in res.options:
        star = "  (recommended)" if o.recommended else ""
        lines.append(
            f"- {o.option_id} {o.label}: +{inr(o.cost_delta_inr)}, risk -{o.risk_reduction:.0%}, "
            f"saves {o.orders_saved}/{len(rep.orders_at_risk)} orders{star}\n  {o.rationale}"
        )
    if not res.options and res.notes:
        lines.append(res.notes)
    lines.append("To act on an option (emails, PO), ask the SupplyShock Orchestrator.")
    return "\n".join(lines)
