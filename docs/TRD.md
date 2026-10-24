# SupplyShock — Technical Requirements Document (TRD)

> **Status note (24 Oct 2026):** this doc describes the planned design. What is actually built, and what was cut (Payment Protocol, Watchtower, remote multi-agent messaging), is in [06_FINAL_STATUS.md](06_FINAL_STATUS.md). Where they differ, that page wins.

| Field | Value |
|---|---|
| Version | 1.0 |
| Date | 2026-10-24 |
| Related | [PRD.md](PRD.md), [02_AGENTS_AND_WORKFLOW.md](02_AGENTS_AND_WORKFLOW.md) |

---

## 1. System architecture

```
ASI:One ──(Agent Chat Protocol)──► Orchestrator (uAgent, mailbox / hosted on Agentverse)
                                       │  ├─ Planner (ASI1 LLM → JSON DAG → validator)
                                       │  ├─ DAG Executor (asyncio, retries, timeouts)
                                       │  ├─ Card Renderer (Interactive Cards + text fallback)
                                       │  ├─ Payment Handler (Payment Protocol)
                                       │  └─ Session Store (agent storage / SQLite)
                                       │
                 typed uAgents messages (pydantic Models)
     ┌────────────┬────────────┬───────┴─────┬────────────┬─────────────┐
  Sentinel     Exposure     Sourcing      Strategy      Action      Watchtower
```

- Each agent is a **separate uAgent process** with its own address, registered on Agentverse (mailbox mode for local dev; hosted or deployed for the demo).
- Every agent includes the **Chat Protocol** (`publish_manifest=True`) so it can be discovered individually. The specialists also include a private **task protocol** for typed calls between agents.

## 2. Technology stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.11+ | uAgents ecosystem |
| Agent framework | `uagents`, `uagents-core` | Native Agentverse, Chat Protocol and Payment Protocol |
| LLM | **ASI1** (`https://api.asi1.ai/v1/chat/completions`, OpenAI-compatible) | Fits the challenge; good for reasoning and function calls |
| Data models | `pydantic` (uAgents `Model`) | Typed messages |
| Supply graph | `networkx` + SQLite (`sqlite3` / `sqlmodel`) | Light, easy to seed |
| Geo | `haversine`, Nominatim / Open-Meteo geocoding | Distance to event |
| HTTP | `httpx` (async) + `tenacity` (retries) | Reliability |
| Email | Resend API or SMTP (Gmail app password) | Real RFQ delivery |
| PDF | `reportlab` | Draft PO |
| Config | `python-dotenv` | Secrets |
| Tests | `pytest`, `pytest-asyncio`, `respx` (HTTP mocks) | Reliability |
| Deploy | Agentverse hosted / Render / Railway / a VM with mailbox | **Required:** agents must stay online after the deadline for judges |

## 3. External data sources

| Source | Endpoint | Use | Auth |
|---|---|---|---|
| GDACS | `https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH` | Live disasters with geo and alert level | None |
| GDELT DOC 2.0 | `https://api.gdeltproject.org/api/v2/doc/doc?query=...&mode=artlist&format=json` | News: strikes, port closures, fires | None |
| Open-Meteo | `https://api.open-meteo.com/v1/forecast` | Wind and rain forecast at supplier coordinates | None |
| Open-Meteo Geocoding | `https://geocoding-api.open-meteo.com/v1/search` | Place name → coordinates | None |
| Frankfurter | `https://api.frankfurter.app/latest` | Live FX for costs | None |
| ASI1 | `https://api.asi1.ai/v1/chat/completions` | Intent, planning, relevance, drafting | API key |
| Resend / SMTP | — | Send RFQs | API key |

> Check the exact query parameters for each API during Day 1. Wrap every call behind an adapter so it can be swapped.

## 4. Data model (SQLite)

```sql
suppliers(id PK, name, city, country, lat, lon, tier, quality_rating, risk_score, email, lead_time_days)
materials(id PK, name, category, unit, unit_cost_inr)
supplier_materials(supplier_id FK, material_id FK, price_inr, moq, capacity_per_week, is_primary BOOL)
products(id PK, name, sell_price_inr)
bom(product_id FK, material_id FK, qty_per_unit)
inventory(material_id FK, on_hand_qty, daily_consumption, safety_stock)
customer_orders(id PK, customer, product_id FK, qty, due_date, value_inr, status)
incidents(id PK, event_json, status, created_at, chosen_option_json, outcome)
actions_log(id PK, incident_id FK, type, target, status, payload_json, ts)
```

The seed dataset ("Apex Components Pvt Ltd") has about 25 suppliers across Chennai, Pune, Gujarat, Shenzhen, Penang, Stuttgart and Monterrey, 30 materials, 8 products and 40 open orders, so that any major event has visible exposure.

## 5. Message schemas (uAgents `Model`)

```python
class GeoPoint(Model):  lat: float; lon: float
class Event(Model):
    event_id: str; type: str; title: str; center: GeoPoint; radius_km: float
    severity: str; start: str; end: str | None; sources: list[str]; confidence: float

class EventQuery(Model):   incident_id: str; task_id: str; location: str | None; type: str | None; horizon_days: int = 7
class EventResult(Model):  incident_id: str; task_id: str; events: list[Event]; degraded: bool = False; notes: str = ""

class MaterialExposure(Model):
    material_id: str; name: str; supplier_ids: list[str]; cover_days: float
    stockout_date: str | None; severity: str
class ExposureRequest(Model): incident_id: str; task_id: str; event: Event
class ExposureReport(Model):
    incident_id: str; task_id: str; suppliers_hit: list[str]; materials: list[MaterialExposure]
    orders_at_risk: list[str]; revenue_at_risk_inr: float; trace: list[str]

class Alternate(Model): supplier_id: str; name: str; material_id: str; price_inr: float; lead_time_days: int; distance_km: float; score: float
class SourcingRequest(Model): incident_id: str; task_id: str; material_ids: list[str]; exclude_zone: Event
class SourcingResult(Model):  incident_id: str; task_id: str; alternates: list[Alternate]; search_radius_km: float

class Option(Model): option_id: str; label: str; actions: list[dict]; cost_delta_inr: float; risk_reduction: float; orders_saved: int; recommended: bool; rationale: str
class StrategyRequest(Model): incident_id: str; task_id: str; exposure: ExposureReport; sourcing: SourcingResult
class StrategyOptions(Model): incident_id: str; task_id: str; options: list[Option]

class ActionRequest(Model): incident_id: str; task_id: str; option: Option; approved_by: str
class ActionResult(Model):  type: str; target: str; status: str; detail: str
class ActionReceipt(Model): incident_id: str; task_id: str; results: list[ActionResult]

class WatchSubscribe(Model): incident_id: str; event: Event; user_sender: str; interval_min: int = 30
class WatchAlert(Model):     incident_id: str; change: str; new_severity: str
class TaskError(Model):      incident_id: str; task_id: str; code: str; message: str; retryable: bool
```

## 6. Chat Protocol integration (Orchestrator)

```python
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatMessage, ChatAcknowledgement, TextContent, EndSessionContent, chat_protocol_spec)

agent = Agent(name="supplyshock-orchestrator", seed=ORCH_SEED, port=8000, mailbox=True)
chat = Protocol(spec=chat_protocol_spec)

@chat.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=now(), acknowledged_msg_id=msg.msg_id))
    text = " ".join(c.text for c in msg.content if isinstance(c, TextContent))
    await orchestrator.handle(ctx, sender, text)   # plan → execute → respond with cards

@chat.on_message(ChatAcknowledgement)
async def on_ack(ctx, sender, msg): pass

agent.include(chat, publish_manifest=True)
```

**Agentverse README** (for ASI:One discovery): clear title, description, keywords (*supply chain, disruption, procurement, manufacturing, risk, RFQ, cyclone, port strike*) and example prompts. ASI:One's search ranks agents largely on this README.

## 7. Planner & executor

### 7.1 Planner
1. ASI1 call with a system prompt containing the intent list, the tool catalogue and a JSON schema for `Plan {tasks:[{id, agent, action, args, depends_on[]}]}`.
2. Check the result with pydantic: agent and action must be in the allow-list, and the DAG must have no cycles.
3. If validation fails, use the **template plan** for that intent (deterministic).

### 7.2 Executor
```python
async def run_dag(plan):
    while pending:
        ready = [t for t in pending if deps_done(t)]
        results = await asyncio.gather(*[dispatch(t) for t in ready], return_exceptions=True)
        for t, r in zip(ready, results):
            if is_error(r): handle_failure(t, r)  # retry → fallback → degrade → replan
            else: store(t, r); maybe_replan(t, r)
```
- Dispatch: `ctx.send(agent_addr, Request)`. Replies are matched by `task_id` through an `asyncio.Future` registry.
- Timeout 20 s, retries 2 (backoff 1 s, 3 s).
- **Human gates:** a task with `agent="HUMAN"` pauses the DAG. The state is saved, and the next chat message or card response resumes it.

### 7.3 Failure matrix
| Failure | Handling |
|---|---|
| Specialist timeout | Retry ×2, then run a local fallback function in the Orchestrator (same code imported) and mark the result degraded |
| GDACS / GDELT error | Use the other source, then the cache, then ask the user for event details |
| Geocode fails | Ask the user to clarify the location |
| Zero exposure | Report "not exposed" with the closest supplier distance, and offer a watch |
| No alternates | Widen the radius 500 → 2000 km → global; suggest safety stock |
| Email fails | Retry once, then save as a draft and show the text in chat |
| Payment rejected or timeout | Keep the free report and offer to retry the payment |
| Invalid LLM JSON | Re-ask once, then use the template plan |

## 8. Interactive Cards

Follow the ASI1 Interactive Cards docs: https://innovationlab.fetch.ai/resources/docs/interactive-cards/asi-interactive-cards

- A `cards.py` module has one builder per card (`plan_card`, `event_card`, `exposure_card`, `options_carousel`, `approval_card`, `receipt_card`, `setup_form`).
- Each builder returns `(card_payload, text_fallback)`. Send both so non-card clients still work.
- Card button and form submissions come back as chat messages. They are routed by `incident_id` + `action` to resume the DAG.

> Check the exact card JSON schema and resource-content type against the docs on Day 1, then build a "hello card" test first.

## 9. Payment Protocol

```python
from uagents_core.contrib.protocols.payment import (
    payment_protocol_spec, RequestPayment, CommitPayment, CompletePayment, RejectPayment, Funds)
```
Flow: approval → Orchestrator sends `RequestPayment(funds=[Funds(amount="0.5", currency="FET")], deadline_seconds=300, reference=incident_id, ...)` → user wallet sends `CommitPayment(transaction_id)` → Orchestrator verifies the transaction on-chain (testnet) → `CompletePayment` → the Action task resumes. On `RejectPayment` or timeout, it falls back to the free summary.

> Check the exact field names against the current `uagents-core` version.

## 10. Exposure algorithm
```
for supplier in suppliers:
    d = haversine(supplier, event.center)
    if d <= event.radius_km * buffer(1.2): hit.add(supplier)
for material in materials supplied (primary) by hit suppliers:
    cover_days = on_hand / daily_consumption
    disruption_days = estimate(event.type, severity)   # table: cyclone orange = 10–14 days
    alt_lead = min lead time of non-hit suppliers for material
    severity = CRITICAL if cover_days < alt_lead else HIGH if cover_days < disruption_days else MED/LOW
    orders_at_risk += orders whose product BOM uses material and due_date < today + disruption_days
revenue_at_risk = Σ order.value for orders_at_risk
```

## 11. Option scoring
`score = w1·risk_reduction + w2·orders_saved_ratio − w3·norm(cost_delta) − w4·norm(time_to_effect)`, with default weights 0.4 / 0.3 / 0.2 / 0.1. The LLM writes only the `rationale` text from the computed numbers; it never decides the numbers.

## 12. Repository structure
```
SupplyShock/
├── agents/
│   ├── orchestrator/  (agent.py, planner.py, executor.py, cards.py, payment.py, session.py)
│   ├── sentinel/      (agent.py, gdacs.py, gdelt.py, weather.py)
│   ├── exposure/      (agent.py, graph.py)
│   ├── sourcing/      (agent.py, ranker.py)
│   ├── strategy/      (agent.py, scoring.py)
│   ├── action/        (agent.py, email.py, po_pdf.py)
│   └── watchtower/    (agent.py)
├── shared/            (models.py, config.py, llm.py, logging.py)
├── data/              (seed.sql, seed_generator.py, replay_events/)
├── tests/
├── docs/
├── scripts/run_all.py
├── .env.example
├── requirements.txt
└── README.md
```

## 13. Environment variables
```
ASI1_API_KEY=
AGENTVERSE_API_KEY=
ORCH_SEED= SENTINEL_SEED= EXPOSURE_SEED= SOURCING_SEED= STRATEGY_SEED= ACTION_SEED= WATCH_SEED=
RESEND_API_KEY=          # or SMTP_HOST/SMTP_USER/SMTP_PASS
RFQ_FROM_EMAIL=
DEMO_SUPPLIER_INBOX=     # all demo RFQs go to a controlled inbox
PAYMENT_ENABLED=true
FET_NETWORK=testnet
REPLAY_MODE=false
```

## 14. Security & safety
- Every outward action needs explicit approval from the user on a card.
- In demo mode, every email goes to `DEMO_SUPPLIER_INBOX` (never to real outside suppliers).
- Seeds and keys are kept only in `.env`, which is listed in `.gitignore`.
- LLM output is never executed as code. Plans are checked against the allow-list.

## 15. Testing
- Unit tests: haversine, cover days, scoring, plan validator.
- Contract tests: every Model round-trip.
- HTTP mocks for GDACS, GDELT and Open-Meteo, including failure cases.
- End-to-end: a script sends a ChatMessage to the Orchestrator and checks that the final receipt arrives.
- Chaos test: kill the Sourcing agent and check that the result is degraded but the workflow still completes.

## 16. Observability
- JSON logs with `incident_id`, `task_id`, `agent`, `latency_ms` and `status`.
- A `/status` chat command returns the DAG state for the current incident (also useful in the demo).
