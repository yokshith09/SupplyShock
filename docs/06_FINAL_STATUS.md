# SupplyShock — Final Status (24 Oct 2026, submission day)

This page is the source of truth for what is built. Earlier planning docs (PRD, TRD, Agents & Workflow, Team Plan) describe the full vision; where they differ, this page wins.

## Built and verified
| Capability | Status | Evidence |
|---|---|---|
| Agent Chat Protocol on Agentverse (mailbox) | Done | Orchestrator answers in ASI:One |
| ASI Interactive Cards: options carousel, review card, receipt card | Done | Rendered in ASI:One; text fallback for every card |
| Intent classification (keyword fallback; ASI1 optional) | Done | `agents/orchestrator/intents.py`, tests |
| Task DAG planner + executor (parallel steps, timeout, retries, degraded fallback, approval gate) | Done | `agents/orchestrator/planner.py`, `executor.py`, tests |
| Sentinel (replay of Cyclone Michaung, GDACS, Open-Meteo, geocoding) | Done | `agents/sentinel` |
| Exposure (supplier→material→BOM→product→order, cover days, ₹ at risk) | Done | `agents/exposure` |
| Sourcing (alternates outside zone, ranking, radius widening) | Done | `agents/sourcing` |
| Strategy (scored options, recommended flag, optional LLM rationale) | Done | `agents/strategy` |
| Action: real email (Resend/SMTP → demo inbox), PO PDF, customer notices | Done | Emails received in the demo inbox |
| Human approval before any outward action | Done | Test proves a plan pick never executes; only explicit approve does |
| Clarifying question for unknown places | Done | `INVALID_INPUT` handled in `dispatcher.py` |
| Incident + action audit log (SQLite) | Done | `agents/orchestrator/store.py` |
| Tests | 145 passing | `python -m pytest tests -q` (offline) |

## Not built (do not claim)
- **Payment Protocol** (pay-per-incident). Designed in the PRD/TRD, cut for time.
- **Watchtower** follow-up alerts and the STATUS follow-up beyond a simple state message.
- **GDELT news adapter**, supplier-check and standalone sourcing intents.
- **Remote multi-agent messaging.** Sentinel, Exposure, Sourcing and Strategy run as in-process services called by the Orchestrator (`DISPATCH_LOCAL_AGENTS`). Typed-protocol agent wrappers for D2's services are being added separately; the Orchestrator does not yet call them over Agentverse.
- **Always-on hosting** unless stated otherwise in the README. The Orchestrator is a mailbox agent: it answers only while its process is running.

## Data honesty
- ERP data is a seeded dataset for a fictional manufacturer ("Apex Components Pvt Ltd").
- The demo event is a recorded real event (Cyclone Michaung, Dec 2023, dates shifted to today) because live GDACS is slow. `REPLAY_MODE=true`.
- Demo emails go to `DEMO_SUPPLIER_INBOX`, never to real suppliers, and the email subject/body name the intended recipient.

## Branches
`main` has everything (D1 and D2 merged). `d1` and `d2` were the working branches.

## Run
See the root [README](../README.md).
