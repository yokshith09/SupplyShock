# SupplyShock ⚡ — Supply-Chain Disruption Agents (Fetch-A-Thon 3.0)

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

From disruption to decision to action, in one ASI:One chat.

SupplyShock is a multi-agent supply-chain disruption responder for manufacturers, built on Fetch.ai **uAgents**, registered on **Agentverse**, and used entirely through **ASI:One** (Agent Chat Protocol + ASI Interactive Cards, no custom frontend).

> *"Cyclone warning on the Tamil Nadu coast, are we exposed?"*
> → event detected → 3 suppliers, 12 orders, ₹1.82 Cr at risk → scored response options (carousel card) → review card → approve → RFQs and expedite requests emailed, purchase-order PDF and customer notices drafted.

## The problem
Manufacturers learn about disruptions (cyclones, port strikes, supplier fires) days late, then spend days in spreadsheets working out which suppliers, materials and customer orders are exposed. SupplyShock does that in one conversation and acts on it after the user approves. Target users: procurement managers, plant heads and SME owners. Details in [docs/01_PROBLEM_STATEMENT.md](docs/01_PROBLEM_STATEMENT.md).

## What it does in ASI:One
1. **Understands** the request (intent + place + event type; ASI1 LLM optional, keyword fallback always on).
2. **Plans** a task DAG and runs it with parallel steps, timeouts, retries and degraded-mode fallbacks.
3. **Sentinel** finds the event (GDACS / Open-Meteo, recorded Cyclone Michaung replay for a repeatable demo).
4. **Exposure** walks supplier → material → BOM → product → order and computes cover days, stock-out dates and ₹ at risk.
5. **Sourcing** finds and ranks alternate suppliers outside the impact zone.
6. **Strategy** generates scored options (cost, risk reduction, orders saved) with a recommended one.
7. The user picks a plan on an **Interactive Card carousel**, reviews it on a **review card**, and approves.
8. **Action** carries out the approved plan: real emails (Resend/SMTP, redirected to a demo inbox), a draft PO PDF and customer notices. Nothing is sent without explicit approval. A receipt card lists every action.

Every card also has a full text fallback, and every step works with typed commands (`select OPT-C`, `approve`, `cancel`).

## Agents
| Agent | Role | Where it runs |
|---|---|---|
| **Orchestrator** (`agents/orchestrator`) | Chat Protocol + cards, planning, executor, approval gate | Registered on Agentverse (mailbox) |
| **Action** (`agents/action`) | Emails, PO PDF, customer notices | Agentverse agent + in-process service |
| Sentinel, Exposure, Sourcing, Strategy (`agents/<name>/service.py`) | Detect, calculate, recommend | In-process services called by the Orchestrator (`DISPATCH_LOCAL_AGENTS`); typed-protocol agent wrappers are being added |

| Agent | Agentverse address |
|---|---|
| SupplyShock Orchestrator | `agent1qgt7x0cakv0htfapv9yecj8mqw28jsyramh03aqztfquzlavcadc7nczfdz` |
| SupplyShock Action | `agent1q0tl4ypgxlsdw3srtkt46g96dec0kdes4qefj5clqz70ngwytekxq0qr5v2` |

Agentverse profile URL: _add after publishing_ · ASI:One shared chat: _add_ · Demo video: _add_

**Honest scope.** The company's ERP data (suppliers, BOM, inventory, orders) is a seeded demo dataset for a fictional manufacturer, "Apex Components Pvt Ltd". External signals use a recorded real event in replay mode (`REPLAY_MODE=true`) because live GDACS is slow and unreliable. Demo emails are redirected to a controlled inbox (`DEMO_SUPPLIER_INBOX`), never to real suppliers. Not built: Payment Protocol, Watchtower follow-up alerts.

## Run and test it
Requires Python 3.11+.
```bash
git clone https://github.com/yokshith09/SupplyShock.git
cd SupplyShock
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
python data/seed_generator.py   # builds the demo ERP database (required)
python -m pytest tests -q       # 145 tests, no network needed
```
Edit `.env`: set `ORCH_SEED` to any secret phrase, `REPLAY_MODE=true`, `DISPATCH_LOCAL_AGENTS=sentinel,exposure,sourcing,strategy,action`, and (for real emails) `RESEND_API_KEY`, `RFQ_FROM_EMAIL=onboarding@resend.dev`, `DEMO_SUPPLIER_INBOX=<your Resend signup email>`. Without email settings the Action agent returns copy-ready drafts instead of sending.

Try the flow in a terminal, no ASI:One needed:
```bash
python scripts/chat_cli.py "Cyclone warning on the Tamil Nadu coast, are we exposed?" --yes
```
Run the agent for ASI:One:
```bash
python -m agents.orchestrator.agent
```
To host it on another machine, follow [docs/08_HOSTING.md](docs/08_HOSTING.md) (`python scripts/run_all.py`). Open the inspector link it prints, click **Connect → Mailbox**, then chat with the agent from ASI:One (Agents enabled) and send: *Cyclone warning on the Tamil Nadu coast, are we exposed?*

## Documents
**[Final status (what is built)](docs/06_FINAL_STATUS.md)** · **[Hosting handoff](docs/08_HOSTING.md)** · **[Submission pack](docs/07_SUBMISSION.md)** · [Problem Statement](docs/01_PROBLEM_STATEMENT.md) · [Agents & Workflow](docs/02_AGENTS_AND_WORKFLOW.md) · [Deliverables & Tech Stack](docs/03_DELIVERABLES_REQUIREMENTS_TECHSTACK.md) · [PRD](docs/PRD.md) · [TRD](docs/TRD.md) · [Team Plan](docs/04_TEAM_PLAN.md)
