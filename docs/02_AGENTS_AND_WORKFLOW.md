# SupplyShock — Agents, Workflow & Multi-Step Orchestration

> **Status note (24 Oct 2026):** this doc describes the planned design. What is actually built, and what was cut (Payment Protocol, Watchtower, remote multi-agent messaging), is in [06_FINAL_STATUS.md](06_FINAL_STATUS.md). Where they differ, that page wins.

## 1. Agent roster

There are 7 agents, all built with uAgents and registered on Agentverse. Only the **Orchestrator** speaks the Chat Protocol to ASI:One. The specialists talk to it through typed uAgents messages, and each specialist also exposes the Chat Protocol so it can be discovered and used on its own.

| # | Agent | Role | Tools / Data |
|---|---|---|---|
| 0 | **Orchestrator ("Shock Commander")** | Understands intent, builds the plan (a task DAG), sends tasks, combines results, renders cards, handles payment | ASI1 LLM, plan state store, Payment Protocol |
| 1 | **Sentinel Agent** | Detects and normalises disruption events | GDACS API, GDELT DOC 2.0 API, Open-Meteo, geocoding |
| 2 | **Exposure Agent** | Maps an event to the supply graph and calculates impact | Supply graph (SQLite + NetworkX), inventory, open orders |
| 3 | **Sourcing Agent** | Finds and ranks alternate suppliers | Supplier directory, geo-distance, risk score, Frankfurter FX |
| 4 | **Strategy Agent** | Generates and scores mitigation options | Scoring model, ASI1 for explanations |
| 5 | **Action Agent** | Carries out the approved plan | SMTP / Resend email, PO generator (PDF), webhook to ERP |
| 6 | **Watchtower Agent** | Keeps monitoring after the incident and pushes updates | Interval tasks, Sentinel re-queries |

## 2. Multi-step planning, reasoning and orchestration

This is the core of what judges will look at. The Orchestrator does not run a fixed script. It **plans, reasons, carries out, checks and re-plans.**

### 2.1 Planning (intent → task DAG)
1. **Intent classification** with ASI1 into one of:
   - `SCAN`: "Are we exposed to anything right now?"
   - `EVENT_IMPACT`: "Cyclone near Chennai, what's our exposure?"
   - `SUPPLIER_CHECK`: "Is Supplier X safe?"
   - `SOURCE_ALT`: "Find a backup for aluminium ingot."
   - `STATUS`: "Update on the Chennai incident?"
2. **Entity extraction:** location, event type, supplier, material, time horizon.
3. **Plan generation:** the LLM drafts a **task DAG** as JSON. The plan is then **checked against a schema and a list of allowed tools** before it runs. Example for `EVENT_IMPACT`:

```
T1 Sentinel.resolve_event(location="Chennai", type="cyclone")
T2 Exposure.compute(event=T1)                    depends_on: T1
T3 Sourcing.find_alternates(materials=T2.at_risk) depends_on: T2   ┐ run in
T4 Exposure.stock_cover(materials=T2.at_risk)     depends_on: T2   ┘ parallel
T5 Strategy.generate_options(T2, T3, T4)         depends_on: T3,T4
T6 [HUMAN] user selects option via card          depends_on: T5
T7 Action.execute(option=T6)                     depends_on: T6
T8 Watchtower.subscribe(event=T1)                depends_on: T7
```

### 2.2 Reasoning
- **Deterministic where it matters:** exposure, stock cover and cost are calculated in code, not guessed by the LLM.
- **LLM where it helps:** understanding intent, deciding whether a news story is relevant, explaining trade-offs, drafting RFQ emails.
- **Confidence gating:** every Sentinel event has a confidence score (number of sources, severity, distance to the supplier). If confidence is below 0.5, the Orchestrator asks the user to confirm before going further.
- **Explainability:** every recommendation comes with a "why" trace, e.g. *"Supplier S-07 is 42 km from the cyclone track; Material M-12 cover = 6 days < lead time of alternate (9 days) → stock-out risk HIGH."*

### 2.3 Orchestration
- Runs the DAG in dependency order and runs independent tasks **in parallel** (T3 and T4).
- Uses a **correlation ID** per incident; all agent messages carry `incident_id` and `task_id`.
- **Timeouts and retries:** each task has a 20 s timeout and 2 retries with exponential backoff.
- **Fallbacks:**
  - GDACS down → fall back to GDELT news. Both down → ask the user to describe the event manually.
  - No alternates within 500 km → widen to the country, then to global, and flag the higher lead time.
  - Email send fails → save the RFQ as a draft and give the user a copy-ready version.
- **Re-planning:** if a result changes the situation (for example, an alternate supplier is itself inside the disaster zone), the Orchestrator adds new tasks to the DAG instead of failing.
- **Human-in-the-loop:** no outward action (email, PO) happens without the user's approval on a card.

### 2.4 Plan state machine
```
RECEIVED → PLANNED → RUNNING → AWAITING_APPROVAL → EXECUTING → MONITORING → CLOSED
                         ↘ DEGRADED (partial results, recovered) ↗
                         ↘ FAILED (error explained to user, retry offered)
```

## 3. End-to-end workflow in ASI:One (demo script)

**Step 1: Trigger**
> User: *"There's a cyclone warning for the Tamil Nadu coast. Are we exposed?"*

**Step 2: Plan preview (text + card)**
Orchestrator: *"I'll (1) confirm the event, (2) check which of your suppliers and orders are affected, (3) find backups, (4) give you options. ~1 min."*

**Step 3: Event card**
Sentinel returns: *Cyclone "X", GDACS Orange alert, landfall expected near Chennai in 36 h, wind 120 km/h, 3 news sources, confidence 0.86.*

**Step 4: Exposure card (review / detail view)**
- 3 suppliers within the impact radius (S-03 Chennai Castings, S-07 Sriperumbudur Electronics, S-11 Ennore Port forwarding)
- 5 materials, 12 open customer orders, **₹1.82 Cr revenue at risk**
- Worst item: *ECU housing (M-12): 6 days of cover vs. 14 days of expected disruption → stock-out on 30 Oct*

**Step 5: Options carousel card**
| Option | Cost Δ | Risk ↓ | Orders saved |
|---|---|---|---|
| A. Expedite current stock by air before landfall | +₹4.2 L | 55% | 7/12 |
| B. Switch M-12 to Pune Diecast (S-21) | +₹2.8 L | 80% | 11/12 |
| C. Split order 50/50 S-03 / S-21 + safety stock | +₹3.5 L | 90% | 12/12 ⭐ recommended |

**Step 6: Approval card**
The user picks C and reviews the actions: 2 RFQs, 1 expedite email, 1 draft PO, 2 customer notices → **Approve**.

**Step 7: Payment (bonus)**
Free tier includes exposure analysis. **Execution with sourcing and RFQs costs a small FET fee** through the Payment Protocol (`RequestPayment` → user commits → `CompletePayment`).

**Step 8: Execution receipt card**
*"✅ RFQ sent to Pune Diecast & Coimbatore Alloys, ✅ expedite request sent to Chennai Castings, ✅ PO-2026-0412 drafted, ✅ 2 customer notices drafted. I'm watching the cyclone and will alert you if it changes."*

**Step 9: Follow-up (Watchtower)**
> Later: *"Update on Chennai?"* → status card: cyclone downgraded, RFQ replies received, best quote highlighted.

## 4. Message contracts (summary)

| Message | From → To | Key fields |
|---|---|---|
| `EventQuery` / `EventResult` | Orch ↔ Sentinel | location, type, horizon / events[], confidence |
| `ExposureRequest` / `ExposureReport` | Orch ↔ Exposure | event_geo / suppliers[], materials[], orders[], revenue_at_risk, cover_days |
| `SourcingRequest` / `SourcingResult` | Orch ↔ Sourcing | materials[], exclude_zone / alternates[] ranked |
| `StrategyRequest` / `StrategyOptions` | Orch ↔ Strategy | exposure, alternates / options[] with scores |
| `ActionRequest` / `ActionReceipt` | Orch ↔ Action | option, approvals / results[] (status per action) |
| `WatchSubscribe` / `WatchAlert` | Orch ↔ Watchtower | incident_id, thresholds / delta |

Full schemas are in [TRD.md](TRD.md).

## 5. Architecture diagram

```
                ┌──────────────┐
   User ⇄ ASI:One ⇄ Chat Protocol ⇄ │ Orchestrator │ ⇄ Payment Protocol
                └──────┬───────┘
          uAgents msgs │ (incident_id, task_id)
   ┌────────┬──────────┼──────────┬──────────┬───────────┐
Sentinel  Exposure  Sourcing   Strategy    Action    Watchtower
 │GDACS     │SQLite    │Supplier  │Scoring    │Email/PDF   │interval
 │GDELT     │NetworkX  │dir + FX  │+ ASI1     │ERP webhook │re-check
 │Open-Meteo│                                              │
```
