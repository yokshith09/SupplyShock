# SupplyShock Exposure

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

Works out which suppliers, materials and customer orders a disruption puts at risk, with stock-out dates, severity and revenue at risk.

Part of **SupplyShock**, a multi-agent supply-chain disruption responder (Fetch-A-Thon 3.0). The SupplyShock Orchestrator calls this agent as one step of its plan; you can also chat with it directly in ASI:One.

## Example prompts
- "Cyclone near Chennai, what's our exposure?"
- "What if a flood hits Pune?"
- "Exposure to an earthquake in Shenzhen"

## Interface
- Typed protocol `supplyshock-exposure-task`: `ExposureRequest` -> `ExposureReport` (or `TaskError`). Models: `shared/models.py`.
- Agent Chat Protocol: plain-text questions, plain-text answers.

## Run and test on its own
```bash
pip install -r requirements.txt
python data/seed_generator.py        # ERP demo data (Exposure, Sourcing, Strategy)
python -m agents.exposure.agent        # prints the agent address and an Agentverse inspector link
pytest tests/exposure
```
Env vars: EXPOSURE_SEED, EXPOSURE_PORT (8102), DB_PATH, SEED_TODAY.

## Agentverse profile (copy into the agent page)
- **Title:** SupplyShock Exposure
- **Description:** Works out which suppliers, materials and customer orders a disruption puts at risk, with stock-out dates, severity and revenue at risk.
- **Keywords:** supply chain, exposure, stock-out, inventory, procurement, revenue at risk, manufacturing
- **Example prompts:** see above.
