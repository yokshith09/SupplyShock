"""Strategy: turn exposure + sourcing into scored mitigation options. Owner: D2.

    async def handle(req: StrategyRequest) -> StrategyOptions

Numbers come from code (options.py, scoring.py). The LLM only writes the rationale text from
the computed numbers; if it fails, template sentences are used and degraded=True.
Env: STRATEGY_LLM=false turns the LLM off (templates only).
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sqlite3
import time

from agents.strategy import options, scoring
from data import db
from shared import llm
from shared.constants import ErrorCode
from shared.models import ServiceError, StrategyOptions, StrategyRequest

logger = logging.getLogger("supplyshock.strategy")

LLM_TIMEOUT_S = 10
_DISRUPTION_RE = re.compile(r"Expected disruption for an? .+?: (\d+) days")


def disruption_days(trace: list[str]) -> int:
    """Read the disruption length Exposure used (its trace line); fall back to 14 days."""
    for line in trace:
        match = _DISRUPTION_RE.search(line)
        if match:
            return int(match.group(1))
    return options.DISRUPTION_DAYS_FALLBACK


def _rs(amount: float) -> str:
    return f"Rs {amount / 1e5:.1f} L" if amount >= 1e5 else f"Rs {amount:,.0f}"


def template_rationale(d: options.Draft, total: int) -> str:
    saved = len(d.saved_orders)
    if d.option_id == "OPT-A":
        return (
            f"Fastest to act (about {d.time_to_effect_days} days) for {_rs(d.cost_delta_inr)} extra, but it "
            f"relies on suppliers inside the impact zone shipping before landfall; saves {saved} of {total} orders."
        )
    if d.option_id == "OPT-B":
        return (
            f"Moves the at-risk materials to suppliers outside the zone for {_rs(d.cost_delta_inr)} extra; "
            f"the first deliveries take up to {d.time_to_effect_days} days, so it saves {saved} of {total} orders."
        )
    return (
        f"Expedited stock bridges the first days and backup suppliers cover the rest, saving "
        f"{saved} of {total} orders for {_rs(d.cost_delta_inr)} extra."
    )


async def llm_rationales(drafts: list[options.Draft], total: int) -> dict[str, str]:
    facts = [
        {
            "option_id": d.option_id,
            "label": d.label,
            "extra_cost_inr": d.cost_delta_inr,
            "orders_saved": len(d.saved_orders),
            "orders_total": total,
            "days_to_take_effect": d.time_to_effect_days,
            "reliability": d.reliability,
        }
        for d in drafts
    ]
    messages = [
        {
            "role": "system",
            "content": "You explain supply-chain mitigation options to a procurement manager. For each "
            "option write one or two plain sentences (max 35 words) explaining the trade-off. Use ONLY the "
            "numbers given; never invent or change numbers. Write money as 'Rs X L'. Never say "
            "'guarantee': every option has a reliability below 100%.",
        },
        {"role": "user", "content": f"Options: {facts}"},
    ]
    data = await llm.complete_json(messages, schema_hint='{"OPT-A": "text", "OPT-B": "text", "OPT-C": "text"}', timeout_s=LLM_TIMEOUT_S)
    if not isinstance(data, dict):
        raise llm.LLMError("rationale JSON was not an object")
    return {k: str(v).strip() for k, v in data.items() if isinstance(v, str) and v.strip()}


def _use_llm() -> bool:
    return os.getenv("STRATEGY_LLM", "true").strip().lower() not in {"0", "false", "no", "off"}


async def handle(req: StrategyRequest) -> StrategyOptions:
    started = time.perf_counter()
    exposure = req.exposure
    if not exposure.orders_at_risk:
        return StrategyOptions(
            incident_id=req.incident_id,
            task_id=req.task_id,
            notes="No orders are at risk, so no mitigation is needed. Keep monitoring the event.",
        )
    if not db.db_path().exists():
        raise ServiceError(ErrorCode.INTERNAL.value, "ERP data is not loaded. Run `python data/seed_generator.py` first.")

    disruption = disruption_days(exposure.trace)
    try:
        drafts = options.build_drafts(exposure, req.sourcing, disruption)
    except sqlite3.Error as exc:
        logger.exception("strategy db error")
        raise ServiceError(ErrorCode.INTERNAL.value, f"ERP database error: {exc}", retryable=True) from exc

    if not drafts:
        return StrategyOptions(
            incident_id=req.incident_id,
            task_id=req.task_id,
            notes="Every affected material has enough stock to outlast the disruption. No action needed now.",
        )

    total = len(exposure.orders_at_risk)
    revenue = exposure.revenue_at_risk_inr
    scores = {}
    for d in drafts:
        rr = d.reliability * (d.saved_revenue_inr / revenue) if revenue else 0.0
        scores[d.option_id] = scoring.score(
            rr, len(d.saved_orders), total, d.cost_delta_inr, revenue, d.time_to_effect_days, disruption
        )
    best = max(drafts, key=lambda d: (scores[d.option_id], len(d.saved_orders)))

    degraded, notes = False, []
    rationales = {d.option_id: template_rationale(d, total) for d in drafts}
    if _use_llm():
        try:
            written = await asyncio.wait_for(llm_rationales(drafts, total), LLM_TIMEOUT_S + 2)
            rationales.update({k: v for k, v in written.items() if k in rationales})
        except Exception as exc:  # LLM is optional: keep the template text
            logger.warning("strategy rationale LLM failed: %r", exc)
            degraded = True
            notes.append("Explanations use standard wording because the AI writer was unavailable.")

    result = StrategyOptions(
        incident_id=req.incident_id,
        task_id=req.task_id,
        options=[
            options.to_option(d, revenue, d is best, rationales[d.option_id]) for d in drafts
        ],
        degraded=degraded,
        notes=" ".join(notes),
    )
    logger.info(
        "strategy done",
        extra={
            "incident_id": req.incident_id,
            "task_id": req.task_id,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "recommended": best.option_id,
            "scores": scores,
        },
    )
    return result
