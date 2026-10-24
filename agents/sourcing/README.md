# SupplyShock Sourcing

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

Finds and ranks backup suppliers outside a disruption zone by price, lead time, quality and risk, widening the search when nothing is nearby.

Part of **SupplyShock**, a multi-agent supply-chain disruption responder (Fetch-A-Thon 3.0). The SupplyShock Orchestrator calls this agent as one step of its plan; you can also chat with it directly in ASI:One.

## Example prompts
- "Backup suppliers for M-12 near Chennai"
- "Find alternates for ECU housing if Chennai is hit"
- "Backups for M-22 near Ennore"

## Interface
- Typed protocol `supplyshock-sourcing-task`: `SourcingRequest` -> `SourcingResult` (or `TaskError`). Models: `shared/models.py`.
- Agent Chat Protocol: plain-text questions, plain-text answers.

## Run and test on its own
```bash
pip install -r requirements.txt
python data/seed_generator.py        # ERP demo data (Exposure, Sourcing, Strategy)
python -m agents.sourcing.agent        # prints the agent address and an Agentverse inspector link
pytest tests/sourcing
```
Env vars: SOURCING_SEED, SOURCING_PORT (8103), DB_PATH.

## Agentverse profile (copy into the agent page)
- **Title:** SupplyShock Sourcing
- **Description:** Finds and ranks backup suppliers outside a disruption zone by price, lead time, quality and risk, widening the search when nothing is nearby.
- **Keywords:** supply chain, sourcing, alternate supplier, procurement, RFQ, manufacturing
- **Example prompts:** see above.
