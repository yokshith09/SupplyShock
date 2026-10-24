# SupplyShock — Team Plan: Task Division, Contracts & Git Workflow

> **Audience:** both developers. Read all of this before writing code.
> **Based on:** [PRD](PRD.md), [TRD](TRD.md), [Agents & Workflow](02_AGENTS_AND_WORKFLOW.md), [Deliverables](03_DELIVERABLES_REQUIREMENTS_TECHSTACK.md).
> **Rule zero:** contracts first, code second. Nobody starts parallel coding until **Phase 0** (Section G) is merged into `main`.

---

## Who is who

| Role | Name (fill in) | GitHub handle | Workstream |
|---|---|---|---|
| **Developer 1 (D1)** | | | **"Conversation & Execution":** everything the user sees and every outward action |
| **Developer 2 (D2)** | | | **"Intelligence & Data":** everything that detects, calculates and recommends |

> Pick roles once and don't swap mid-hackathon. D1 suits whoever enjoys protocols, UX and integration. D2 suits whoever enjoys data, APIs and algorithms.

---

# A. Project overview

### A.1 What we are building
7 uAgents running as separate processes, all registered on Agentverse. The user talks only to the **Orchestrator** through ASI:One (Agent Chat Protocol). The Orchestrator plans a task DAG and calls the specialist agents with typed messages. It shows results as Interactive Cards, takes payment, and then triggers execution.

```
            ASI:One (user)
                 │  Agent Chat Protocol  (+ Payment Protocol)
                 ▼
     ┌─────────────────────────┐
     │  ORCHESTRATOR  [D1]     │  planner · DAG executor · cards · payment · session
     └───┬─────────┬───────────┘
         │ typed uAgents messages (shared/models.py)  ← the contract boundary
  ┌──────┼─────────┬──────────┬───────────┐           ┌────────────────┐
  ▼      ▼         ▼          ▼           ▼           ▼                ▼
SENTINEL EXPOSURE SOURCING  STRATEGY     ACTION [D1]  WATCHTOWER [D1]
 [D2]    [D2]     [D2]      [D2]          email/PDF    re-checks via Sentinel
 GDACS   SQLite   supplier  scoring
 GDELT   NetworkX dir + FX  + rationale
 Meteo
         └──────── data/ (SQLite seed + schema) [D2] ────────┘
```

### A.2 The key architectural rule: logic is separate from transport
Every agent has the **same two-layer layout**:

| File | What it holds | Depends on uAgents? |
|---|---|---|
| `agents/<name>/service.py` | **Pure async business logic.** `async def handle(req: XRequest) -> XResponse` | **No.** Only `shared/models.py` |
| `agents/<name>/agent.py` | Thin wrapper: create the `Agent`, include the protocols, call `service.handle()`, `ctx.send()` the reply | Yes |

Why this matters for a two-person team:
1. **D2 can test every specialist with plain `pytest`**, with no agents running and no network.
2. **D1 can run the whole Orchestrator against D2's `service.handle()` functions in-process** (the "local fallback" from TRD §7.3), or against fixture mocks, before D2's agents are deployed.
3. **Integration is a configuration switch, not a code change:** `DISPATCH_MODE=mock | local | remote`.

### A.3 How a request flows (EVENT_IMPACT)
1. ASI:One → `ChatMessage` → **Orchestrator** (D1)
2. Planner builds a DAG (D1) → Executor dispatches:
3. `EventQuery` → **Sentinel** (D2) → `EventResult`
4. `ExposureRequest` → **Exposure** (D2) → `ExposureReport`
5. In parallel: `SourcingRequest` → **Sourcing** (D2), and stock cover (inside Exposure)
6. `StrategyRequest` → **Strategy** (D2) → `StrategyOptions`
7. Cards → user approves → Payment (D1)
8. `ActionRequest` → **Action** (D1) → `ActionReceipt`
9. `WatchSubscribe` → **Watchtower** (D1) → later `WatchAlert` → user

---

# B. Developer 1: Conversation & Execution

### B.1 Owned folders and files (only D1 edits these)
```
agents/orchestrator/        agent.py, planner.py, executor.py, dispatcher.py,
                            cards.py, payment.py, session.py, intents.py, prompts.py
agents/action/              agent.py, service.py, email_sender.py, po_pdf.py, templates/
agents/watchtower/          agent.py, service.py
agents/*/README_AGENTVERSE.md  (all 7 Agentverse profile READMEs, since D1 owns discovery)
shared/config.py            env loading, settings object
shared/logging.py           JSON logger
shared/dispatch.py          mock | local | remote dispatch switch
scripts/run_all.py          starts all 7 agents
scripts/chat_cli.py         local terminal chat with the Orchestrator (no ASI:One needed)
deploy/                     Render/Railway/Agentverse hosting files
tests/orchestrator/  tests/action/  tests/watchtower/
data/migrations/2xx_*.sql   ONLY the incidents & actions_log tables
requirements/orchestration.txt
```

### B.2 Tasks

| # | Task | Deliverable | Depends on |
|---|---|---|---|
| D1-1 | Orchestrator agent with Chat Protocol, ack handling, mailbox, registered on Agentverse | An agent that echoes messages in ASI:One | Phase 0 |
| D1-2 | `session.py`: per-sender state (active incident, DAG state, last options) in agent storage | Session survives between messages | D1-1 |
| D1-3 | `intents.py` + `prompts.py`: ASI1 intent classification and entity extraction, with a keyword fallback | `classify(text) -> Intent` with 6 intents | `shared/llm.py` (D2) or a stub |
| D1-4 | `planner.py`: LLM → JSON DAG → pydantic validation → template fallback per intent | `build_plan(intent) -> Plan` | contracts |
| D1-5 | `executor.py` + `dispatcher.py`: dependency-ordered async run, parallel tasks, 20 s timeout, 2 retries, degraded mode, re-plan hook, HUMAN gate pause/resume | `run_dag(plan)`, tests with mock agents | D1-4 |
| D1-6 | `shared/dispatch.py`: `DISPATCH_MODE` mock/local/remote | Same Orchestrator code runs in all 3 modes | contracts + fixtures |
| D1-7 | `cards.py`: 7 card builders + text fallbacks (plan, event, exposure, options carousel, approval, receipt, setup form) | Cards render in ASI:One; text fallback in CLI | fixtures |
| D1-8 | Card-response routing (button clicks / form submits → resume DAG) | Approve → execution path works | D1-5, D1-7 |
| D1-9 | `payment.py`: Payment Protocol request/commit/complete/reject, testnet verification, `PAYMENT_ENABLED` switch | Paid execution gate | D1-8 |
| D1-10 | Action agent: RFQ and expedite emails (Resend/SMTP, all sent to `DEMO_SUPPLIER_INBOX`), PO PDF, customer notice drafts, per-action status | `ActionReceipt`, real emails arriving | contracts |
| D1-11 | Watchtower agent: subscribe, interval re-query of Sentinel, change detection, push `WatchAlert` to the user | Follow-up alert in chat | Sentinel (D2) or mock |
| D1-12 | `run_all.py`, `chat_cli.py`, deploy configs, Agentverse READMEs for all 7 agents | One-command start; agents discoverable | all |
| D1-13 | Demo recording, shared chat URL, dashboard submission | Submission complete | integration |

### B.3 D1 testing requirements
- `pytest tests/orchestrator` passes with `DISPATCH_MODE=mock` (no network, no D2 code).
- Executor tests: parallel run, timeout → retry → fallback, invalid LLM plan → template plan, HUMAN gate pause/resume.
- Card builders: snapshot test of the JSON for each fixture; text fallback is never empty.
- Action: email sender tested with a fake transport; PDF file generated and non-empty.
- Manual: `python scripts/chat_cli.py` completes the full flow in mock mode.

---

# C. Developer 2: Intelligence & Data

### C.1 Owned folders and files (only D2 edits these)
```
agents/sentinel/            agent.py, service.py, gdacs.py, gdelt.py, weather.py, geocode.py, dedupe.py
agents/exposure/            agent.py, service.py, graph.py, cover.py
agents/sourcing/            agent.py, service.py, ranker.py, fx.py
agents/strategy/            agent.py, service.py, options.py, scoring.py
shared/llm.py               ASI1 client (chat + JSON mode, retries); D1 consumes it
shared/geo.py               haversine, radius helpers
data/schema.sql             core ERP tables
data/migrations/1xx_*.sql   ERP tables migrations
data/seed_generator.py      "Apex Components Pvt Ltd" dataset
data/replay_events/         recorded past events (Cyclone Michaung, Dec 2023)
data/db.py                  get_connection(), repository functions
tests/fixtures/contracts/   example JSON for every message (D1's mocks read these)
tests/sentinel/ tests/exposure/ tests/sourcing/ tests/strategy/ tests/data/
scripts/send_task.py        send one typed request to one running specialist
requirements/analytics.txt
```

### C.2 Tasks

| # | Task | Deliverable | Depends on |
|---|---|---|---|
| D2-1 | `data/schema.sql`, `db.py`, `seed_generator.py` (25 suppliers in Chennai, Pune, Gujarat, Shenzhen, Penang, Stuttgart, Monterrey; 30 materials; 8 products; 40 orders) | `python data/seed_generator.py` → `data/supplyshock.db` | Phase 0 |
| D2-2 | **Contract fixtures** in `tests/fixtures/contracts/` (one realistic JSON per message type, matching the demo story) | **Unblocks D1.** Due by the end of Phase 0 | contracts |
| D2-3 | `shared/llm.py`: ASI1 client, `complete()` and `complete_json(schema)`, retries, timeout | D1 uses it for intents and planning | Phase 0 |
| D2-4 | Sentinel: GDACS, GDELT and Open-Meteo adapters → standard `Event`; dedupe; confidence score; cache 15 min; source fallback; `REPLAY_MODE` | `EventResult` from live and replay data | D2-1 |
| D2-5 | Exposure: haversine hit test, graph walk Supplier→Material→BOM→Product→Order, cover days, stock-out date, severity, revenue at risk, explanation trace | `ExposureReport` | D2-1, D2-4 |
| D2-6 | Sourcing: alternate search excluding the event zone, ranking, step-by-step radius widening, live FX | `SourcingResult` | D2-1 |
| D2-7 | Strategy: ≥3 options, deterministic scoring (TRD §11), recommended flag, ASI1-written rationale from computed numbers only | `StrategyOptions` | D2-3, D2-5, D2-6 |
| D2-8 | `agent.py` wrappers for all 4 specialists + Chat Protocol on each (for standalone discovery); register on Agentverse | 4 agent addresses | D2-4…7 |
| D2-9 | `scripts/send_task.py` + HTTP-mock failure tests (GDACS down, GDELT 429, empty results) | Reliability evidence for the judges | D2-4…7 |
| D2-10 | Support integration: fix contract mismatches, tune the demo data so the story numbers work out | Demo numbers stable | integration |

### C.3 D2 testing requirements
- `pytest tests/sentinel tests/exposure tests/sourcing tests/strategy tests/data` passes **offline** (HTTP mocked with `respx`).
- Every `service.handle()` output must validate against its pydantic model **and** match its fixture's shape.
- Unit tests: haversine, cover days, severity rules, scoring weights, radius widening, dedupe.
- Failure tests: each external API failing on its own still gives a result (`degraded=True`).
- Manual: `python scripts/send_task.py exposure tests/fixtures/contracts/ExposureRequest.json` against the running agent.

### C.4 Workload balance check
| | D1 | D2 |
|---|---|---|
| Agents | 3 (Orchestrator: heaviest; Action; Watchtower) | 4 (Sentinel: heaviest; Exposure; Sourcing; Strategy) |
| Hard parts | DAG executor, cards, payment, deployment | External APIs, graph math, seed data, LLM client |
| Integration-time load | High (D1 leads integration) | Medium (fixes on own side) |
| Submission work | Video, READMEs, submission | Seed data and demo story tuning |

---

# D. Shared responsibilities and ownership

Some files must be touched by both people. Each has **one owner**. The other developer **never edits it directly**; they open a PR or ask the owner.

| Shared file / component | Owner | Rule for the other developer |
|---|---|---|
| `shared/models.py` (**all message contracts**) | **D1** | Changes go through a PR labelled `contract`, **approved by both**. Additive changes only (new optional fields with defaults) after Phase 0. Never rename or remove a field without agreeing first |
| `shared/constants.py` (intent names, severity levels, action types, error codes) | **D1** | Same as models.py |
| `tests/fixtures/contracts/*.json` | **D2** | D1 reads only. If D1 needs a new fixture, ask in chat or open an issue |
| `shared/llm.py`, `shared/geo.py` | **D2** | D1 imports only |
| `shared/config.py`, `shared/logging.py`, `shared/dispatch.py` | **D1** | D2 imports only |
| `requirements.txt` (root) | **D1** | It contains only `-r requirements/orchestration.txt` and `-r requirements/analytics.txt`. **Nobody edits it after Phase 0** |
| `requirements/orchestration.txt` | D1 | — |
| `requirements/analytics.txt` | D2 | — |
| `.env.example` | **D1** | Split into two marked blocks: `# --- D1: orchestration ---` and `# --- D2: analytics ---`. Each developer edits **only their own block** (different lines → no conflicts) |
| `pyproject.toml` (ruff config, Python version, pytest settings) | **D1** | Frozen after Phase 0 |
| `.gitignore`, `.gitattributes`, `.editorconfig` | **D1** | Frozen after Phase 0 |
| `README.md` (root) | **D1** | D2 sends text for their sections; D1 pastes it in |
| `docs/*` | Author of each doc; D1 for this plan | Edit only your own sections |
| Database: `data/schema.sql` + `1xx` migrations | **D2** | — |
| Database: `2xx` migrations (incidents, actions_log) | **D1** | — |
| Agent seeds and addresses (`.env`) | Each dev for their own agents | Share addresses in `config/agents.json` (see below) |
| `config/agents.json` (agent name → Agentverse address) | **D1** | D2 sends their 4 addresses once in chat; D1 commits them |
| `scripts/run_all.py` | D1 | — |
| CI workflow `.github/workflows/ci.yml` | D1 | — |

---

# E. Integration contracts

> These go into `shared/models.py`, `shared/constants.py` and `tests/fixtures/contracts/` **during Phase 0**. The full schemas are in [TRD §5](TRD.md#5-message-schemas-uagents-model). This section covers the rules on top of them.

### E.1 Common envelope rules (every request/response)
- Every request **and** response carries `incident_id: str` (UUID4) and `task_id: str` (e.g. `"T3"`).
- Every response has `degraded: bool = False` and `notes: str = ""`. If you still return something useful after a partial failure, set `degraded=True` and explain in `notes`.
- A specialist that cannot answer **at all** sends `TaskError(incident_id, task_id, code, message, retryable)` instead of its normal response.
- Money: `float` in **INR**, with the field name ending in `_inr`. Distances end in `_km`. Durations end in `_days` / `_s`.
- Dates are ISO-8601 strings (`"2026-10-30"`) and timestamps are UTC ISO strings (`"2026-10-24T09:15:00Z"`).
- IDs: suppliers `S-01`, materials `M-01`, products `P-01`, orders `O-1001`, options `OPT-A`, POs `PO-2026-0001`.

### E.2 Constants (`shared/constants.py`, owner D1)
```python
class Intent(str, Enum):  SCAN="SCAN"; EVENT_IMPACT="EVENT_IMPACT"; SUPPLIER_CHECK="SUPPLIER_CHECK"; SOURCE_ALT="SOURCE_ALT"; STATUS="STATUS"; HELP="HELP"
class Severity(str, Enum): LOW="LOW"; MED="MED"; HIGH="HIGH"; CRITICAL="CRITICAL"
class EventType(str, Enum): CYCLONE="cyclone"; FLOOD="flood"; EARTHQUAKE="earthquake"; WILDFIRE="wildfire"; STRIKE="strike"; PORT_CLOSURE="port_closure"; FIRE="fire"; SANCTION="sanction"; OTHER="other"
class ActionType(str, Enum): RFQ_EMAIL="rfq_email"; EXPEDITE_EMAIL="expedite_email"; DRAFT_PO="draft_po"; CUSTOMER_NOTICE="customer_notice"
class ErrorCode(str, Enum): TIMEOUT="TIMEOUT"; UPSTREAM_API="UPSTREAM_API"; NOT_FOUND="NOT_FOUND"; INVALID_INPUT="INVALID_INPUT"; INTERNAL="INTERNAL"
```

### E.3 Specialist service signatures (D2 implements, D1 calls)
```python
# agents/sentinel/service.py
async def handle(req: EventQuery) -> EventResult
# agents/exposure/service.py
async def handle(req: ExposureRequest) -> ExposureReport
# agents/sourcing/service.py
async def handle(req: SourcingRequest) -> SourcingResult
# agents/strategy/service.py
async def handle(req: StrategyRequest) -> StrategyOptions
```
**Behaviour guarantees (D2):**
- Never raises for expected failures. Return `degraded=True`, or raise `ServiceError(code, message, retryable)` (defined in `shared/models.py`), which the wrapper turns into `TaskError`.
- Finishes in **≤ 15 s** (the Orchestrator's timeout is 20 s).
- Gives the same output for the same input when `REPLAY_MODE=true` (so the demo is repeatable).
- Sentinel with no events found → `events=[]` (not an error).
- Exposure with no suppliers hit → `suppliers_hit=[]`, `revenue_at_risk_inr=0`.
- Strategy always returns **≥ 3 options with exactly one `recommended=True`**, unless the exposure is empty.

### E.4 Execution service signatures (D1 implements)
```python
# agents/action/service.py
async def handle(req: ActionRequest) -> ActionReceipt     # one ActionResult per action; status ∈ {"done","failed","draft"}
# agents/watchtower/service.py
async def subscribe(req: WatchSubscribe) -> None
async def check(incident_id: str) -> WatchAlert | None
```
`Option.actions` (made by D2's Strategy, carried out by D1's Action) has this fixed shape:
```json
{"type": "rfq_email", "target_supplier_id": "S-21", "material_id": "M-12", "qty": 4000, "need_by": "2026-11-05"}
{"type": "expedite_email", "target_supplier_id": "S-03", "material_id": "M-12", "qty": 2500}
{"type": "draft_po", "target_supplier_id": "S-21", "material_id": "M-12", "qty": 2000, "unit_price_inr": 412.5}
{"type": "customer_notice", "order_id": "O-1007", "kind": "assurance" | "delay", "new_date": "2026-11-09"}
```
Action uses `data/db.py` repository functions (D2) to look up supplier emails and names. **Action never writes SQL directly.**

### E.5 Repository functions (`data/db.py`, D2 owns, both use)
```python
def get_supplier(supplier_id: str) -> dict | None
def list_suppliers() -> list[dict]
def get_material(material_id: str) -> dict | None
def get_order(order_id: str) -> dict | None
def get_connection() -> sqlite3.Connection
```
> D1's tables (incidents, actions_log) are written by **`agents/orchestrator/store.py`** (D1-owned): `save_incident(incident: dict)` and `log_action(incident_id: str, result: dict)`, using `data.db.get_connection()`. That way D1 never waits on D2 and never edits `db.py`.

### E.6 Dispatch contract (`shared/dispatch.py`, D1)
```python
async def call(agent: str, request: Model, timeout_s: float = 20) -> Model
# DISPATCH_MODE=mock   → load tests/fixtures/contracts/<ResponseType>.json
# DISPATCH_MODE=local  → import agents.<agent>.service and await handle(request)
# DISPATCH_MODE=remote → ctx.send(address from config/agents.json), await reply by task_id
```

### E.7 Card contract (D1 internal, consumed only by D1)
`cards.py` builders take **response models** as input, never raw dicts:
`exposure_card(report: ExposureReport) -> tuple[dict, str]`. This means D2 changing internal logic can never break the cards; only a contract change can.

### E.8 Assumptions both developers accept
1. Python **3.11.x**, one virtualenv per laptop, never committed.
2. The single SQLite file `data/supplyshock.db` is **generated, never committed** (`*.db` in `.gitignore`).
3. All demo emails go to `DEMO_SUPPLIER_INBOX`.
4. The demo story numbers (3 suppliers, 12 orders, ₹1.82 Cr) are what the fixtures and the seed data aim for. D2 tunes the seed until live Exposure output roughly matches the fixtures.

---

# F. Git workflow

### F.1 Strategy: trunk-based, with short-lived feature branches
- `main` = always runnable. Protected: no direct pushes after Phase 0, PR required, CI must pass.
- Branch names: `d1/<topic>` and `d2/<topic>`, e.g. `d1/executor`, `d2/sentinel-gdacs`, plus `contract/<topic>` for `shared/models.py` changes.
- Branches live **≤ 1 day**. Small PRs merge often, which is the single biggest protection against conflicts.
- Merge method: **Squash and merge** (one clean commit per feature on `main`).

### F.2 One-time setup (each developer, any OS)
```bash
git clone https://github.com/yokshith09/SupplyShock.git
cd SupplyShock
git config user.name "Your Name"
git config user.email "you@example.com"
git config pull.rebase true
git config core.autocrlf false        # .gitattributes handles line endings
```
Repo owner (yokshith09), once on GitHub: Settings → Branches → add a protection rule for `main`: require a PR, require 1 approval, require status checks (CI).

Environment (Windows PowerShell / macOS / Linux):
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                  # Windows: copy .env.example .env
python data/seed_generator.py
pytest
```

### F.3 Line endings and editor differences (cross-platform safety)
Committed in Phase 0 by D1:
- `.gitattributes`: `* text=auto eol=lf`, `*.png binary`, `*.pdf binary`
- `.editorconfig`: UTF-8, LF, 4-space indent for `.py`, final newline, trim trailing whitespace
- `ruff` formatter and linter config in `pyproject.toml`. Everyone runs `ruff format . && ruff check .` before committing, whatever their IDE.
- IDE folders (`.vscode/`, `.idea/`) go in `.gitignore`. Keep personal IDE settings out of the repo.

### F.4 Daily loop (both developers)
```bash
# start of each task
git checkout main
git pull                                   # rebase-pull, gets the other dev's merged work
git checkout -b d2/exposure-graph          # your prefix

# work… commit small and often
ruff format . && ruff check . && pytest tests/exposure
git add agents/exposure tests/exposure     # add YOUR paths explicitly, avoid `git add -A`
git commit -m "feat(exposure): graph walk and cover days"

# sync with main at least twice a day
git fetch origin
git rebase origin/main                     # resolve conflicts if any (see F.7)
git push -u origin d2/exposure-graph       # after a rebase: git push --force-with-lease

# open the PR
gh pr create --base main --title "feat(exposure): graph walk" --body "What/why/how tested"
```

### F.5 Commit message format (Conventional Commits)
`<type>(<scope>): <summary>`. Types: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`, `contract`.
Scopes: `orchestrator`, `action`, `watchtower`, `sentinel`, `exposure`, `sourcing`, `strategy`, `data`, `shared`, `deploy`.

### F.6 Code review and merge rules
| PR touches | Reviewer | Merge when |
|---|---|---|
| Only your own folders | Other dev (a quick look, ≤ 30 min) | CI green + 1 approval. If the reviewer is unreachable for 2 h during the hackathon, the author may merge their own-folder PRs |
| `shared/models.py`, `shared/constants.py`, fixtures | **Both must approve** | CI green, and both developers have pulled the change before continuing |
| A file owned by the other dev | **Not allowed.** Ask the owner instead | — |

PR checklist (paste into the PR description):
- [ ] Only touches files I own (or is a `contract/` PR approved by both)
- [ ] `ruff format`, `ruff check`, `pytest` pass locally
- [ ] No secrets, no `.env`, no `.db` files
- [ ] New env vars added to my block of `.env.example`
- [ ] New dependency added to my `requirements/*.txt` with a pinned version

### F.7 Resolving conflicts safely
Conflicts should be rare because files are separated. If one happens:
```bash
git fetch origin
git rebase origin/main
# Git stops at a conflict
git status                               # see conflicted files
# open each file and keep BOTH sides when they're independent additions
ruff format . && pytest                  # must pass before continuing
git add <file>
git rebase --continue
git push --force-with-lease              # never plain --force
```
- If the conflict is in a file **you don't own**, stop. Run `git rebase --abort`, and agree with the owner on a call.
- If a rebase gets messy: `git rebase --abort`, then make a fresh branch from `main` and cherry-pick your commits.
- Never `git push --force` to `main`. Never commit a resolution without running the tests.

### F.8 Dependencies, env vars, and the database
- **Dependencies:** add to **your own** `requirements/*.txt` with an exact pin (`httpx==0.27.2`). Before merging, check that the shared libraries (`uagents`, `uagents-core`, `pydantic`) use **the same pinned version** in both files. Those three are pinned only in `requirements/orchestration.txt` (D1), and D2 does not re-list them.
- **Env vars:** add new keys only to your block in `.env.example`, with a dummy value and a comment. Real values go only in `.env` (gitignored). Share real secrets over a private channel, **never in Git or PR comments**.
- **Database:** never edit `schema.sql` after Phase 0. Add a new numbered migration in **your own range** (D2: `100–199`, D1: `200–299`). `seed_generator.py` applies `schema.sql` and then all migrations in number order. After pulling, re-run `python data/seed_generator.py` to rebuild your local DB (it's disposable).

### F.9 Integration branch (Phase 3 only)
For the final integration both developers work on `integration/e2e`, cut from `main`. D1 drives and D2 pushes fixes to their own folders on the same branch (still different files, so no conflicts). Merge back to `main` with a PR when the checklist in H passes. Tag the release with `git tag v1.0-submission && git push --tags`.

---

# G. Development timeline

```
            Phase 0         Phase 1 (Day 1)        Phase 2 (Day 2)        Phase 3 (Day 3)
           (together,       (parallel)             (parallel)             (together)
            2–3 h)
D1  ──[skeleton+contracts]──[Orch chat+session ──[cards+approval  ──┐
                            +planner+executor     +payment+Action    │
                            (mock mode)]          +Watchtower]       ├──[integration, remote mode,
D2  ──[fixtures+schema   ]──[seed+llm+Sentinel ──[Sourcing+Strategy ─┘   deploy, demo, submit]
       (together)           +Exposure (offline)]  +4 agent wrappers
                                                  +failure tests]
```

### Phase 0: Contracts and skeleton (sequential, both together, ~2–3 h). Everyone waits for this to finish.
| Step | Who | Output |
|---|---|---|
| 0.1 | D1 | Folder skeleton with empty `__init__.py`, `pyproject.toml`, `.gitattributes`, `.editorconfig`, `.gitignore` update, root `requirements.txt` + 2 sub-files, `.env.example` with 2 blocks, CI workflow (ruff + pytest) |
| 0.2 | D1 (both review) | `shared/models.py` and `shared/constants.py` with all schemas from TRD §5 plus the rules in E.1 |
| 0.3 | D2 | `tests/fixtures/contracts/*.json`, one per model, matching the demo story; `tests/test_contracts.py` that loads each fixture into its model |
| 0.4 | D2 | `data/schema.sql` + an empty `db.py` with function signatures |
| 0.5 | D1 | `shared/dispatch.py` mock mode working against the fixtures |
| 0.6 | Both | Interactive Cards "hello card" check and Payment Protocol field check against the current Fetch.ai docs; fix models if needed |
| ✅ | Both | PR `contract/phase0` approved by both and merged. **Parallel work starts here** |

### Phase 1: Day 1 (parallel)
| D1 | D2 |
|---|---|
| D1-1 Orchestrator + Chat Protocol on Agentverse | D2-1 Seed generator + db.py |
| D1-2 Session | D2-3 `shared/llm.py` (merge **early**, D1 needs it for D1-3) |
| D1-3 Intents (stub the LLM until D2-3 merges) | D2-4 Sentinel (GDACS + Open-Meteo first, GDELT next) |
| D1-4 Planner, D1-5 Executor, D1-6 dispatch modes | D2-5 Exposure |
| **Exit:** `chat_cli.py` full text flow in **mock** mode | **Exit:** Sentinel + Exposure `service.handle()` pass offline tests on the replay event |

**Sync point (end of Day 1, 15 min):** D1 switches to `DISPATCH_MODE=local` for Sentinel and Exposure, and fixes any mismatch.

### Phase 2: Day 2 (parallel)
| D1 | D2 |
|---|---|
| D1-7 Cards, D1-8 card routing | D2-6 Sourcing |
| D1-10 Action agent (emails + PDF) | D2-7 Strategy |
| D1-9 Payment | D2-8 Agent wrappers for the 4 specialists + Agentverse registration; send addresses to D1 |
| D1-11 Watchtower (calls the Sentinel service locally) | D2-9 Failure tests + `send_task.py`; GDELT adapter |
| **Exit:** in `local` mode, full flow up to the receipt in ASI:One | **Exit:** all 4 specialists live on Agentverse, offline tests green |

### Phase 3: Day 3 (together, sequential)
1. `integration/e2e` branch → `DISPATCH_MODE=remote` → full flow in ASI:One (D1 drives, D2 fixes)
2. Chaos test: stop Sourcing → confirm degraded completion
3. Payment on testnet end to end
4. Deploy all 7 agents so they stay up (D1); final seed tuning (D2)
5. Agentverse READMEs, shared chat URL, video, submission (D1); description, fact-check of numbers (D2)
6. Merge to `main`, tag `v1.0-submission`

### Hard dependencies (what must happen first)
| Blocked task | Waits for |
|---|---|
| All parallel work | Phase 0 merged |
| D1-3 intents with a real LLM | D2-3 `shared/llm.py` |
| D1 `local` dispatch for a specialist | That specialist's `service.handle()` merged |
| D1-10 Action supplier lookups | D2-1 `db.py` `get_supplier` |
| D1-11 Watchtower live checks | D2-4 Sentinel |
| Phase 3 remote mode | D2-8 addresses in `config/agents.json` |

---

# H. Integration and testing checklist

### H.1 Before each merge to `main`
- [ ] CI green (ruff + pytest)
- [ ] `tests/test_contracts.py` passes (fixtures ↔ models)
- [ ] App still starts: `python scripts/run_all.py` runs for 30 s with no tracebacks

### H.2 Contract conformance (end of Phase 2)
- [ ] Every D2 `service.handle()` output validates against its model and matches its fixture's shape
- [ ] `DISPATCH_MODE=mock`, `local` and `remote` each complete the EVENT_IMPACT flow
- [ ] `Option.actions` produced by Strategy are all carried out by Action without errors
- [ ] `incident_id` / `task_id` are the same across every log line of one incident

### H.3 End-to-end in ASI:One (remote mode)
- [ ] Orchestrator is found by searching "SupplyShock" / "supply chain disruption" in ASI:One
- [ ] "Cyclone warning on Tamil Nadu coast, are we exposed?" → plan card → event card → exposure card
- [ ] Options carousel shows ≥ 3 options, with one recommended
- [ ] Approval → payment request → testnet payment → execution
- [ ] Receipt card shows each action's status; RFQ emails arrive in the demo inbox; PO PDF created
- [ ] "Update on Chennai?" → Watchtower status reply
- [ ] SCAN, SUPPLIER_CHECK and SOURCE_ALT intents each give a sensible answer
- [ ] Text fallback readable if cards don't render

### H.4 Reliability
- [ ] GDACS blocked → GDELT/cache used, `degraded` noted to the user
- [ ] Sourcing agent stopped → Orchestrator uses the local fallback and completes
- [ ] Invalid LLM plan → template plan used
- [ ] Email failure → draft shown in chat
- [ ] Payment rejected → free summary kept, retry offered
- [ ] Location that doesn't exist → clarifying question, no crash

### H.5 Release
- [ ] No secrets in the repo (`git log -p | grep -i "api_key"` is clean)
- [ ] README: setup on Windows and macOS/Linux, run steps, test steps, agent addresses
- [ ] All 7 Agentverse profile URLs listed in the README
- [ ] Agents running on hosted infrastructure (not a laptop) for judging
- [ ] Shared chat URL, video, description submitted on the dashboard
- [ ] `v1.0-submission` tag pushed

---

# Shared development standards (applies to both)

| Area | Rule |
|---|---|
| Language / runtime | Python **3.11.x** on every laptop. Check with `python --version` |
| Framework | `uagents` + `uagents-core`, versions pinned once in Phase 0 |
| Style | `ruff format` (line length 100) + `ruff check`. Type hints on every public function |
| Naming | Modules and functions `snake_case`, classes and Models `PascalCase`, constants `UPPER_SNAKE`, agent names `supplyshock-<name>` |
| Imports | Absolute (`from shared.models import Event`). No imports across agent folders **except** the Orchestrator importing `agents.<x>.service` in local mode |
| Async | All I/O is async (`httpx.AsyncClient`). No `requests`, no blocking `time.sleep` |
| Errors | Expected failure → `degraded=True` or `ServiceError`. Never let an exception escape to the user. Turn errors into a friendly chat message plus a retry option |
| Retries | `tenacity`: 2 retries, exponential backoff 1 s→3 s, only on network or 5xx errors |
| Logging | `shared/logging.get_logger(agent)`. JSON lines with `ts, level, agent, incident_id, task_id, event, latency_ms`. No `print()` in agent code |
| Secrets | Only through `shared/config.settings`. Never hard-code; never log keys |
| Tests | `pytest`, offline by default (`respx` for HTTP). Live API tests marked `@pytest.mark.live` and skipped in CI |
| Debugging | `LOG_LEVEL=DEBUG`; `scripts/chat_cli.py` (D1) and `scripts/send_task.py` (D2) to test one piece at a time |
| Docs / handoff | Each agent folder has a `README.md`: purpose, inputs and outputs (model names), env vars, how to run and test it on its own. Update it in the same PR as the code |
| Definition of done | Code + tests + agent README + `.env.example` entry + merged to `main` |

### Communication rhythm
- **Start of day (10 min):** what I'll merge today, what I need from you.
- **Contract change:** message the other dev **before** opening the `contract/` PR.
- **Blocked > 30 min:** say so right away; use mock/local mode to keep moving.
- **End of day (15 min):** run the integration sync for that phase together.
