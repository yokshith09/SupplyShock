# SupplyShock — Developer 2 task list (with prompts and approval gates)

**How to use this file**
1. Do the tasks **in order**. Start a task only after the previous one is marked ✅.
2. Copy the task's **Prompt** into your AI coding assistant (Claude Code loads [CLAUDE_D2.md](CLAUDE_D2.md) automatically. For other tools, paste CLAUDE_D2.md first).
3. When the assistant reports back, check the **Acceptance** list yourself. Reply `approved T<n>` to let it commit, push and open the PR, or reply with what to fix.
4. Times are targets for today (24 Oct, submit by 17:50 IST). If a task runs over its time box by more than 15 minutes, cut scope (see each task's "Cut if late").

| # | Task | Time box (IST) | Unblocks | Status |
|---|---|---|---|---|
| T0 | Phase 0 D2 part: fixtures + schema | 13:05–13:30 | D1 mock mode | ☐ |
| T1 | `shared/llm.py` + `shared/geo.py` | 13:30–13:45 | D1 intents | ☐ |
| T2 | Seed data + `db.py` | 13:45–14:10 | Exposure, Sourcing, D1 Action | ☐ |
| T3 | Sentinel service (replay + GDACS + Open-Meteo) | 14:10–14:50 | Exposure | ☐ |
| T4 | Exposure service | 14:50–15:25 | Strategy, D1 cards | ☐ |
| T5 | Sourcing service | 15:25–15:45 | Strategy | ☐ |
| T6 | Strategy service | 15:45–16:05 | D1 approval + Action | ☐ |
| T7 | Agent wrappers + Agentverse registration + always-on hosting | 16:05–16:35 | Phase 3 | ☐ |
| T8 | Integration support + demo numbers check | 16:35–17:30 | Submission | ☐ |
| S1 | Stretch: failure tests + `send_task.py` | only if time | Reliability bonus | ☐ |
| S2 | Stretch: GDELT news adapter | only if time | Real-time bonus | ☐ |

**The demo story every task must match** (from [02_AGENTS_AND_WORKFLOW.md](../02_AGENTS_AND_WORKFLOW.md)):
Cyclone near Chennai (replay: **Cyclone Michaung, Dec 2023**, centre ≈ 13.08 N, 80.27 E, radius ≈ 150 km, GDACS Orange).
Hit suppliers: **S-03 Chennai Castings, S-07 Sriperumbudur Electronics, S-11 Ennore Port Forwarding** → 5 materials, **12 open orders**, revenue at risk ≈ **₹1.82 Cr**. Worst material: **M-12 ECU housing**, 6 days of cover vs 14 days of disruption → stock-out around 30 Oct. Best alternate for M-12: **S-21 Pune Diecast**; second: **Coimbatore Alloys**. Options: **OPT-A** expedite by air, **OPT-B** switch M-12 to S-21, **OPT-C** split 50/50 + safety stock (recommended).

---

## T0: Phase 0 D2 part: contract fixtures + DB schema
**Skip if** `tests/fixtures/contracts/` and `data/schema.sql` are already on `main`.

**Files:** `tests/fixtures/contracts/*.json`, `tests/test_contracts.py`, `data/schema.sql`, `data/__init__.py`

**Prompt**
```
Task T0 from docs/d2/TASKS.md. Follow docs/d2/CLAUDE_D2.md.

First run `git checkout main && git pull` and check whether shared/models.py exists.

1. Create tests/fixtures/contracts/ with ONE realistic JSON file per message model
   from docs/TRD.md §5 (EventQuery, EventResult, ExposureRequest, ExposureReport,
   SourcingRequest, SourcingResult, StrategyRequest, StrategyOptions, ActionRequest,
   ActionReceipt, WatchSubscribe, WatchAlert, TaskError). File name = model name.
   Use the demo story in docs/d2/TASKS.md exactly (Cyclone Michaung replay, S-03/S-07/S-11,
   12 orders, ₹1.82 Cr, M-12 cover 6 days, S-21 alternate, OPT-A/B/C with OPT-C recommended).
   Use ONE shared incident_id across all fixtures. Option.actions must follow the shapes
   in docs/04_TEAM_PLAN.md §E.4.
2. If shared/models.py exists: write tests/test_contracts.py that loads every fixture
   into its model and asserts it validates. If it does not exist: write the test so it
   skips with a clear message, and tell me what D1 still needs to add.
3. Create data/schema.sql from docs/TRD.md §4 (ERP tables only: suppliers, materials,
   supplier_materials, products, bom, inventory, customer_orders). Do NOT create
   incidents or actions_log, which are D1's (2xx migrations). Add a data/migrations/ folder
   with a .gitkeep.
Run pytest tests/test_contracts.py, then stop and report as CLAUDE_D2.md §5 says.
```
**Acceptance**
- [ ] 13 fixture files, all sharing one `incident_id`, numbers matching the demo story
- [ ] `pytest tests/test_contracts.py` passes (or skips cleanly if models.py is missing)
- [ ] `schema.sql` has the 7 ERP tables only
- [ ] D1 told the fixtures are ready (message them the PR link)

**Cut if late:** skip WatchSubscribe/WatchAlert fixtures.

---

## T1: `shared/llm.py` (ASI1 client) + `shared/geo.py`
**Files:** `shared/llm.py`, `shared/geo.py`, `tests/data/test_geo.py`, `tests/data/test_llm.py`, `requirements/analytics.txt`, D2 block of `.env.example`

**Prompt**
```
Task T1 from docs/d2/TASKS.md. Follow docs/d2/CLAUDE_D2.md.

1. shared/llm.py: an async ASI1 client for the OpenAI-compatible endpoint
   https://api.asi1.ai/v1/chat/completions (key from env ASI1_API_KEY, model from env
   ASI1_MODEL with default "asi1-mini"; check the current model name in the ASI1 docs
   and tell me if it differs). Expose:
     async def complete(messages: list[dict], temperature: float = 0.2, timeout_s: float = 15) -> str
     async def complete_json(messages: list[dict], schema_hint: str, timeout_s: float = 15) -> dict
   complete_json asks for JSON only, strips ```json fences, parses it, and retries once
   with a "return valid JSON only" message if parsing fails. Use httpx.AsyncClient and
   tenacity (2 retries, backoff 1s→3s, only on network errors / 5xx). Raise a clear
   LLMError on final failure. Never log the API key.
2. shared/geo.py: haversine_km(lat1, lon1, lat2, lon2) -> float and
   within_radius(point, center, radius_km, buffer=1.2) -> bool.
3. Tests: geo with known distances (Chennai 13.08,80.27 → Pune 18.52,73.86 ≈ 915 km great-circle, within ±2%); llm with
   respx mocks (success, fenced JSON, invalid JSON then valid, 500 then success).
4. Add httpx, tenacity, respx, pytest-asyncio with pinned versions to
   requirements/analytics.txt (do not re-list uagents/pydantic). Add ASI1_API_KEY and
   ASI1_MODEL to the "# --- D2: analytics ---" block of .env.example (create the block if
   the file exists but has no block. If .env.example doesn't exist, tell me instead).
Run the tests, then stop and report.
```
**Acceptance**
- [ ] Tests pass offline
- [ ] D1 can `from shared.llm import complete_json`
- [ ] No API key in code or logs

**Cut if late:** skip the retry-on-invalid-JSON test.

---

## T2: Seed data + `db.py`
**Files:** `data/seed_generator.py`, `data/db.py`, `tests/data/test_seed.py`

**Prompt**
```
Task T2 from docs/d2/TASKS.md. Follow docs/d2/CLAUDE_D2.md.

1. data/db.py:
     get_connection() -> sqlite3.Connection   (path from env DB_PATH, default data/supplyshock.db, row_factory=sqlite3.Row)
     get_supplier(id) -> dict | None, list_suppliers() -> list[dict],
     get_material(id) -> dict | None, get_order(id) -> dict | None,
     suppliers_for_material(material_id) -> list[dict]   (joined with supplier_materials)
     materials_for_supplier(supplier_id, primary_only=True) -> list[dict]
     products_using_material(material_id) -> list[dict]
     open_orders_for_products(product_ids: list[str]) -> list[dict]
     inventory_for(material_id) -> dict | None
2. data/seed_generator.py: deletes and recreates the DB, applies data/schema.sql then
   every data/migrations/*.sql in number order, then inserts a DETERMINISTIC dataset
   for "Apex Components Pvt Ltd" (fixed values or random.seed(42)):
   ~25 suppliers (Chennai, Sriperumbudur, Ennore, Coimbatore, Pune, Gujarat, Shenzhen,
   Penang, Stuttgart, Monterrey) with real lat/lon, emails like s03@supplyshock.demo,
   30 materials, 8 products, BOM rows, inventory, 40 open orders with due dates from
   today to +30 days.
   The data MUST reproduce the demo story in docs/d2/TASKS.md for the Michaung replay
   event: exactly S-03, S-07, S-11 inside 150 km × 1.2 of (13.08, 80.27); they are
   primary suppliers for 5 materials; those materials' products have 12 open orders due
   within 14 days totalling ≈ ₹1.82 Cr (±3%); M-12 has 6 days of cover; S-21 Pune
   Diecast and a Coimbatore Alloys supplier also supply M-12 (S-21 cheapest overall).
   Coimbatore must be OUTSIDE the impact radius.
3. tests/data/test_seed.py builds a temp DB and asserts the story numbers above.
Run the tests, then stop and report the story numbers it produced.
```
**Acceptance**
- [ ] `python data/seed_generator.py` creates the DB in under 5 s
- [ ] Test confirms 3 hit suppliers, 5 materials, 12 orders, ≈ ₹1.82 Cr, M-12 = 6 days
- [ ] `*.db` is not committed
- [ ] D1 told that `get_supplier` / `get_connection` are ready

**Cut if late:** 15 suppliers and 20 materials are enough, as long as the story numbers hold.

---

## T3: Sentinel service
**Files:** `agents/sentinel/{__init__,service,gdacs,weather,geocode,replay,dedupe}.py`, `data/replay_events/michaung_2023.json`, `tests/sentinel/`

**Prompt**
```
Task T3 from docs/d2/TASKS.md. Follow docs/d2/CLAUDE_D2.md.

Build agents/sentinel/service.py: async def handle(req: EventQuery) -> EventResult.
1. replay.py: if env REPLAY_MODE=true, return the event from
   data/replay_events/michaung_2023.json (write that file: Cyclone Michaung, type cyclone,
   centre 13.08/80.27, radius_km 150, severity Orange, sources ["GDACS (replay)"],
   confidence 0.86). It must equal the event in tests/fixtures/contracts/EventResult.json:
   dates are shifted so start = today and end = today + 14 days, with the original
   Dec 2023 dates kept in the JSON as metadata. Same input → same output.
2. geocode.py: place name → (lat, lon) using the Open-Meteo geocoding API, with a small
   built-in dictionary first (Chennai, Tamil Nadu, Pune, Gujarat, Shenzhen, Penang, Stuttgart,
   Monterrey) so the demo never depends on it.
3. gdacs.py: fetch active events from the GDACS event list API (check the current
   endpoint/params at gdacs.org), map them to Event (type, centre, severity from
   alertlevel, a radius by type/severity table, sources ["GDACS"]).
4. weather.py: Open-Meteo forecast for a point → flag severe wind (> 60 km/h) or rain
   (> 100 mm/day) in the next horizon_days as an extra low-confidence Event.
5. dedupe.py: merge events of the same type within 200 km; confidence = 0.5 + 0.15 per
   extra source, + severity bonus, capped at 0.95.
6. handle(): resolve location → query GDACS and weather in parallel (asyncio.gather) →
   filter to events within 500 km of the location (or all events if no location) →
   dedupe → sort by confidence. If GDACS fails, keep the weather results and set
   degraded=True with a note. If everything fails, return events=[], degraded=True.
   Cache live results for 15 min in memory.
7. Tests (offline, respx): replay mode, GDACS success, GDACS down → degraded, unknown
   place, no events.
Run the tests, then stop and report.
```
**Acceptance**
- [ ] `REPLAY_MODE=true` returns the Michaung event matching the fixture
- [ ] Live mode works once against the real APIs (run it manually and paste the output)
- [ ] GDACS down → degraded result, not a crash

**Cut if late:** drop `weather.py`; replay + GDACS only.

---

## T4: Exposure service
**Files:** `agents/exposure/{__init__,service,graph,cover}.py`, `tests/exposure/`

**Prompt**
```
Task T4 from docs/d2/TASKS.md. Follow docs/d2/CLAUDE_D2.md.

Build agents/exposure/service.py: async def handle(req: ExposureRequest) -> ExposureReport,
following the algorithm in docs/TRD.md §10, using only data/db.py and shared/geo.py.
1. graph.py: suppliers inside event radius × 1.2 → their primary materials → products
   using them (BOM) → open orders due within disruption_days.
2. cover.py: cover_days = on_hand / daily_consumption; stockout_date = today + cover_days;
   disruption_days from a table by event type + severity (cyclone Orange = 14, Red = 21,
   flood = 10, earthquake = 21, strike = 7, default 7);
   severity: CRITICAL if cover_days < min lead time of a non-hit alternate,
   HIGH if cover_days < disruption_days, MED if < 2× disruption_days, else LOW.
3. revenue_at_risk_inr = sum of order values at risk (count each order once).
4. trace: plain-English lines explaining each step with numbers, e.g.
   "S-03 Chennai Castings is 12 km from the cyclone centre (radius 180 km)".
5. No suppliers hit → empty lists, revenue 0, a trace line naming the closest supplier
   and its distance.
6. Sort materials by severity, then cover_days ascending.
Tests: on the seeded DB + Michaung event, assert the demo story numbers and that the
output equals the ExposureReport fixture in shape and key values; a far-away event gives
zero exposure. Run the tests, then stop and report the real output next to the fixture.
```
**Acceptance**
- [ ] Michaung → S-03/S-07/S-11, 5 materials, 12 orders, ≈ ₹1.82 Cr, M-12 CRITICAL or HIGH
- [ ] Output validates as `ExposureReport` and matches the fixture's shape
- [ ] Runs in < 1 s

**Cut if late:** a simpler severity rule (HIGH if cover < disruption, else LOW).

---

## T5: Sourcing service
**Files:** `agents/sourcing/{__init__,service,ranker,fx}.py`, `tests/sourcing/`

**Prompt**
```
Task T5 from docs/d2/TASKS.md. Follow docs/d2/CLAUDE_D2.md.

Build agents/sourcing/service.py: async def handle(req: SourcingRequest) -> SourcingResult.
1. For each material_id: suppliers_for_material(), excluding suppliers inside
   req.exclude_zone (radius × 1.2).
2. ranker.py: score = 0.4·price_score + 0.3·lead_time_score + 0.2·quality_rating_norm
   + 0.1·(1 − risk_score); normalise price and lead time within the candidates (lower is
   better). Return the top 3 per material, sorted by score.
3. Radius widening: first only suppliers within 1,500 km of the event centre; if none,
   go national (same country), then global. Set search_radius_km to the radius used
   (0 = global) and add a note when it widened.
4. fx.py: convert foreign supplier prices to INR with the Frankfurter API
   (https://api.frankfurter.app/latest?from=USD&to=INR etc.), cached 1 h, with fixed
   fallback rates if the API fails (set degraded=True in that case).
Tests: M-12 under Michaung → S-21 Pune Diecast first, Coimbatore Alloys present, no
hit supplier present; widening case; FX failure → fallback + degraded.
Run the tests, then stop and report.
```
**Acceptance**
- [ ] S-21 ranked first for M-12; no in-zone suppliers returned
- [ ] FX failure doesn't break it
- [ ] Output validates as `SourcingResult`

**Cut if late:** skip FX (all prices already INR in the seed) and skip widening.

---

## T6: Strategy service
**Files:** `agents/strategy/{__init__,service,options,scoring}.py`, `tests/strategy/`

**Prompt**
```
Task T6 from docs/d2/TASKS.md. Follow docs/d2/CLAUDE_D2.md.

Build agents/strategy/service.py: async def handle(req: StrategyRequest) -> StrategyOptions.
1. options.py builds at least 3 options from the exposure + sourcing results:
   OPT-A "Expedite current stock by air": expedite_email actions to hit suppliers for
         CRITICAL/HIGH materials; cost = air freight premium (configurable, default 8% of
         the material value); orders saved = orders whose materials arrive before stock-out.
   OPT-B "Switch <material> to <best alternate>": rfq_email + draft_po to the top
         alternate for each CRITICAL/HIGH material; cost = price difference × qty.
   OPT-C "Split 50/50 + safety stock": half from the current supplier (expedite), half
         from the top alternate (rfq + draft_po), plus customer_notice "assurance" for
         at-risk orders.
   Action dicts MUST follow docs/04_TEAM_PLAN.md §E.4 exactly (type, target_supplier_id,
   material_id, qty, need_by / unit_price_inr / order_id, kind, new_date).
2. scoring.py: TRD §11. score = 0.4·risk_reduction + 0.3·orders_saved_ratio
   − 0.2·norm(cost_delta) − 0.1·norm(time_to_effect). Highest score → recommended=True
   (exactly one). The weights and the cost/risk assumptions are constants at the top of
   the file.
3. rationale: one or two sentences per option written by shared.llm.complete() from the
   COMPUTED numbers only (pass them in the prompt; the LLM must not change them). If the LLM
   fails, use a template sentence and set degraded=True.
4. Empty exposure → options=[] with a note.
Tests: Michaung story → 3 options, OPT-C recommended, all actions valid for §E.4;
LLM failure → template rationale; cost/risk numbers identical with or without the LLM.
Run the tests (mock the LLM), then stop and report the 3 options as a table.
```
**Acceptance**
- [ ] 3 options, exactly one recommended (OPT-C for the demo)
- [ ] Every action dict matches §E.4 (D1's Action agent can carry it out unchanged)
- [ ] Numbers come from code; the LLM only writes text

**Cut if late:** template rationales only, no LLM.

---

## T7: Agent wrappers + Agentverse registration + always-on hosting
**Files:** `agents/{sentinel,exposure,sourcing,strategy}/agent.py`, `agents/{…}/README.md`, `requirements/analytics.txt`, D2 block of `.env.example`

**Prompt**
```
Task T7 from docs/d2/TASKS.md. Follow docs/d2/CLAUDE_D2.md.

For each of sentinel, exposure, sourcing, strategy create agents/<name>/agent.py:
1. uagents Agent named "supplyshock-<name>", seed from env <NAME>_SEED, mailbox=True,
   its own port (sentinel 8101, exposure 8102, sourcing 8103, strategy 8104).
2. A task Protocol: on its request model → await service.handle(req) → ctx.send(sender, response);
   on ServiceError → send TaskError; on any other exception → TaskError(code="INTERNAL",
   retryable=True). Log incident_id/task_id/latency_ms.
3. The Agent Chat Protocol (uagents_core.contrib.protocols.chat: ChatMessage,
   ChatAcknowledgement, TextContent, chat_protocol_spec) so each agent is discoverable and
   usable alone in ASI:One: ack every message, run a sensible default (e.g. Sentinel:
   "events near <place>"), reply with a short text summary.
   agent.include(..., publish_manifest=True). Check the current uagents/uagents-core API
   and pin the versions D1 pinned (do not re-list them in analytics.txt).
4. agents/<name>/README.md: purpose, input/output models, env vars, how to run and test it alone.
   Also write the Agentverse profile description (title, 2-line description, keywords,
   3 example prompts) in a section D1 can copy.
5. Tell me exact steps to (a) run each agent, (b) connect its mailbox on Agentverse,
   (c) host it always-on (Agentverse hosted or Render/Railway: recommend the faster one
   for today), and print each agent's address on start-up.
Stop and report the 4 addresses for D1's config/agents.json.
```
**Acceptance**
- [ ] All 4 agents start and print their addresses
- [ ] Each one replies to a chat message in ASI:One / Agentverse inspector
- [ ] Each one is hosted always-on (not on a laptop)
- [ ] Addresses sent to D1

**Cut if late:** register only Sentinel and Exposure as separate agents; D1 runs Sourcing and Strategy in-process (`DISPATCH_MODE=local`). This matches the README agent table.

---

## T8: Integration support + demo numbers check
**Prompt**
```
Task T8 from docs/d2/TASKS.md. Follow docs/d2/CLAUDE_D2.md.

Pull main (D1's work is merged). Run the full flow in DISPATCH_MODE=local, then remote,
using D1's scripts/chat_cli.py with "Cyclone warning on the Tamil Nadu coast, are we exposed?".
1. List every mismatch between my outputs and what D1's code expects (field names,
   missing fields, types, empty values). Fix the ones on my side; write the exact
   change needed for anything on D1's side.
2. Check the numbers shown in each card against the demo story in docs/d2/TASKS.md and
   the fixtures; tune the seed data (only seed_generator.py) if they drift.
3. Run my full test suite.
Stop and report: mismatches found/fixed, final demo numbers, test results.
```
**Acceptance**
- [ ] Full flow works in ASI:One against the hosted agents
- [ ] Card numbers match the demo story
- [ ] All D2 tests pass

---

## S1 (stretch): failure tests + `send_task.py`
```
Task S1 from docs/d2/TASKS.md. Follow docs/d2/CLAUDE_D2.md.
Write scripts/send_task.py <agent> <fixture.json> that sends one typed request to a running
specialist and prints the reply, and add failure tests: GDACS 500, GDACS timeout, Frankfurter
down, LLM down, empty DB results. Each must return degraded or TaskError, never crash.
Stop and report.
```

## S2 (stretch): GDELT news adapter
```
Task S2 from docs/d2/TASKS.md. Follow docs/d2/CLAUDE_D2.md.
Add agents/sentinel/gdelt.py: query the GDELT DOC 2.0 API (mode=artlist, format=json,
last 72 h) for strike / port closure / factory fire / flood near the location; turn article
clusters into low-confidence Events (sources = article domains), feed them into dedupe so they
raise confidence of matching GDACS events. Cache 15 min; on 429 or error → skip and note it.
Respx tests. Stop and report.
```
