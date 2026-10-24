# SupplyShock ⚡ — Supply-Chain Disruption Agents (Fetch-A-Thon 3.0)

From disruption to decision to action, in one ASI:One chat.

A multi-agent supply-chain disruption responder for manufacturers, built on Fetch.ai **uAgents**, registered on **Agentverse**, and used entirely through **ASI:One** (Agent Chat Protocol + Interactive Cards + Payment Protocol).

> *"Cyclone warning on the Tamil Nadu coast, are we exposed?"*
> → live event detected → 3 suppliers, 12 orders, ₹1.82 Cr at risk → 3 scored options → approve → RFQs sent, PO drafted, event watched.

## Documents
| Doc | Contents |
|---|---|
| [Problem Statement](docs/01_PROBLEM_STATEMENT.md) | Problem, users, solution, outcome, metrics |
| [Agents & Workflow](docs/02_AGENTS_AND_WORKFLOW.md) | 7 agents, planning / reasoning / orchestration, demo flow |
| [Deliverables, Requirements & Tech Stack](docs/03_DELIVERABLES_REQUIREMENTS_TECHSTACK.md) | Submission checklist, requirement mapping, build plan |
| [PRD](docs/PRD.md) | Product requirements |
| [TRD](docs/TRD.md) | Technical design, schemas, protocols, failure handling |
| [Team Plan](docs/04_TEAM_PLAN.md) | 2-developer task split, file ownership, integration contracts, Git workflow |

## Agents
Orchestrator · Sentinel · Exposure · Sourcing · Strategy · Action · Watchtower

## Quick start (once the code is in place)
```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
python data/seed_generator.py
python scripts/run_all.py
```
Then open ASI:One and search for **SupplyShock**.

## Agentverse links
_To be added after registration._
