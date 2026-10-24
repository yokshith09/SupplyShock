# SupplyShock — Developer 2 (D2) working rules for AI coding assistants

> Load this file at the start of every D2 session (Claude Code reads it automatically through `CLAUDE.local.md`; for other tools, paste it as the first message).
> Task list with ready-made prompts: [TASKS.md](TASKS.md).

## Who I am working for
I am the coding assistant for **Developer 2 (D2), "Intelligence & Data"**, on SupplyShock, a multi-agent supply-chain disruption responder (Fetch.ai uAgents, Agentverse, ASI:One). Read these before writing code:
- [docs/04_TEAM_PLAN.md](../04_TEAM_PLAN.md): ownership, contracts (section E), Git workflow (section F)
- [docs/TRD.md](../TRD.md): schemas (§5), data model (§4), exposure algorithm (§10), scoring (§11), failure matrix (§7.3)
- [docs/02_AGENTS_AND_WORKFLOW.md](../02_AGENTS_AND_WORKFLOW.md): the demo story

**Deadline: submission by 17:50 IST on 24 Oct 2026.** Prefer a simple version that works over a complete one. Anything marked "stretch" waits until the core flow works.

## What D2 builds
The agents that **detect, calculate and recommend**:

| Component | Folder | Input → Output |
|---|---|---|
| Sentinel | `agents/sentinel/` | `EventQuery` → `EventResult` (GDACS + Open-Meteo, replay mode) |
| Exposure | `agents/exposure/` | `ExposureRequest` → `ExposureReport` |
| Sourcing | `agents/sourcing/` | `SourcingRequest` → `SourcingResult` |
| Strategy | `agents/strategy/` | `StrategyRequest` → `StrategyOptions` |
| Data | `data/` | `schema.sql`, `db.py`, `seed_generator.py`, `replay_events/` |
| Shared helpers | `shared/llm.py`, `shared/geo.py` | ASI1 client, haversine |
| Fixtures | `tests/fixtures/contracts/` | one example JSON per message (D1's mocks use these) |

## Hard rules

### 1. Only touch D2-owned files
**Allowed:** `agents/sentinel/`, `agents/exposure/`, `agents/sourcing/`, `agents/strategy/`, `data/` (except `2xx_*` migrations), `shared/llm.py`, `shared/geo.py`, `tests/fixtures/contracts/`, `tests/sentinel/`, `tests/exposure/`, `tests/sourcing/`, `tests/strategy/`, `tests/data/`, `scripts/send_task.py`, `requirements/analytics.txt`, the `# --- D2: analytics ---` block of `.env.example`, `docs/d2/`.

**Never edit** (owned by D1): `shared/models.py`, `shared/constants.py`, `shared/config.py`, `shared/logging.py`, `shared/dispatch.py`, `agents/orchestrator/`, `agents/action/`, `agents/watchtower/`, root `requirements.txt`, `pyproject.toml`, `.gitignore`, `README.md`, `scripts/run_all.py`.
If a task needs a change there, **stop and write down the exact change for D1** instead of making it.

### 2. Contracts are fixed
- Import message models from `shared/models.py`. Never redefine them locally. If `shared/models.py` isn't on `main` yet, tell the user and use the TRD §5 schemas only for writing fixtures.
- Every request/response carries `incident_id` and `task_id`, copied unchanged from the request into the response.
- Money in INR with names ending `_inr`; distances `_km`; ISO dates.
- Expected failures → return `degraded=True` with a `notes` explanation, or raise `ServiceError`. Never let an exception escape unhandled.
- `service.handle()` finishes in ≤ 15 s.

### 3. Architecture: two layers in every agent
- `agents/<name>/service.py`: `async def handle(req) -> resp`. Pure logic, **no uagents import**.
- `agents/<name>/agent.py`: thin uAgents wrapper that calls `service.handle()`.
- Calculations (distance, cover days, revenue, scores) are **deterministic Python**. The LLM only writes explanation text, never numbers.

### 4. Code standards
Python 3.11, type hints, async I/O with `httpx.AsyncClient`, `tenacity` retries (2, backoff 1 s→3 s), logging through `shared/logging.get_logger` (use `logging.getLogger` if it doesn't exist yet), no `print()` in agent code, secrets only from env. Tests use `pytest` and run **offline** (`respx` for HTTP).

### 5. Approval gate: one task at a time
For each task in [TASKS.md](TASKS.md):
1. Work only on that task's files and scope.
2. When done, **stop** and report:
   - files created or changed
   - test command + its output (it must pass)
   - how the acceptance criteria are met, one line each
   - anything D1 needs to know or change
3. **Wait** for the user to reply `approved T<n>` (or give feedback). Do not start the next task, commit or push before that.
4. After approval: commit (Conventional Commits, e.g. `feat(exposure): graph walk and cover days`), push the branch, open a PR to `main` (own-folder PRs may be merged by D2 if D1 doesn't reply within 15 min, given the deadline), and mark the task ✅ in TASKS.md in the same commit.

### 6. Git
```bash
git checkout main && git pull
git checkout -b d2/<task-slug>
# … work …
git add <only D2 paths>          # never `git add -A`
git commit -m "feat(<scope>): <summary>"
git fetch origin && git rebase origin/main
git push -u origin d2/<task-slug>
gh pr create --base main --fill
```
Never commit `.env`, `*.db`, or API keys. Never force-push `main`.
