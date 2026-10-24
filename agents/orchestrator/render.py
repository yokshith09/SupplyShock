"""Plain-text renderers. Reused as the text fallback for every card in M4 (never empty)."""
from agents.orchestrator.planner import Plan
from shared.models import ActionReceipt, Event, ExposureReport, Option


def inr(x: float) -> str:
    if x >= 1e7:
        return f"₹{x / 1e7:.2f} Cr"
    if x >= 1e5:
        return f"₹{x / 1e5:.1f} L"
    return f"₹{x:,.0f}"


def plan_text(plan: Plan) -> str:
    steps = "\n".join(
        f"  {t.id}. {t.agent}.{t.action}" + (f"  (after {', '.join(t.depends_on)})" if t.depends_on else "")
        for t in plan.tasks)
    return f"Plan ({plan.intent}):\n{steps}" if steps else f"Plan ({plan.intent}): answer directly"


def event_text(e: Event) -> str:
    return (f"Event: {e.title} [{e.type}, {e.severity}] radius {e.radius_km:.0f} km, "
            f"sources: {', '.join(e.sources) or 'n/a'}, confidence {e.confidence:.2f}")


def exposure_text(r: ExposureReport) -> str:
    worst = ""
    if r.materials:
        w = min(r.materials, key=lambda m: m.cover_days)
        worst = (f"\n  Worst: {w.name} ({w.material_id}) {w.cover_days:.0f} days cover, "
                 f"stock-out {w.stockout_date or 'n/a'}, {w.severity}")
    deg = f"\n  (degraded: {r.notes})" if r.degraded else ""
    return (f"Exposure: {len(r.suppliers_hit)} suppliers hit, {len(r.materials)} materials, "
            f"{len(r.orders_at_risk)} orders at risk, {inr(r.revenue_at_risk_inr)} revenue at risk{worst}{deg}")


def options_text(options: list[Option]) -> str:
    lines = []
    for o in options:
        star = "  * recommended" if o.recommended else ""
        lines.append(f"  {o.option_id}. {o.label}: cost +{inr(o.cost_delta_inr)}, "
                     f"risk -{o.risk_reduction:.0%}, orders saved {o.orders_saved}{star}")
        if o.rationale:
            lines.append(f"      why: {o.rationale}")
    return "Options:\n" + "\n".join(lines)


def receipt_text(r: ActionReceipt) -> str:
    icon = {"done": "OK", "draft": "DRAFT", "failed": "FAILED"}
    lines = [f"  [{icon.get(x.status, x.status)}] {x.type} -> {x.target}: {x.detail.splitlines()[0] if x.detail else ''}" for x in r.results]
    return "Execution receipt:\n" + ("\n".join(lines) or "  (no actions)")
