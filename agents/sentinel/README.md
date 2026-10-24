# SupplyShock Sentinel

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

Detects live supply-chain disruptions near a place: cyclones, floods, earthquakes and severe weather, from GDACS and Open-Meteo.

Part of **SupplyShock**, a multi-agent supply-chain disruption responder (Fetch-A-Thon 3.0). The SupplyShock Orchestrator calls this agent as one step of its plan; you can also chat with it directly in ASI:One.

## Example prompts
- "Any disruptions near Chennai?"
- "Is there a cyclone near the Tamil Nadu coast?"
- "Earthquakes near Shenzhen"

## Interface
- Typed protocol `supplyshock-sentinel-task`: `EventQuery` -> `EventResult` (or `TaskError`). Models: `shared/models.py`.
- Agent Chat Protocol: plain-text questions, plain-text answers.

## Run and test on its own
```bash
pip install -r requirements.txt
python data/seed_generator.py        # ERP demo data (Exposure, Sourcing, Strategy)
python -m agents.sentinel.agent        # prints the agent address and an Agentverse inspector link
pytest tests/sentinel
```
Env vars: SENTINEL_SEED, SENTINEL_PORT (8101), REPLAY_MODE, SEED_TODAY.

## Agentverse profile (copy into the agent page)
- **Title:** SupplyShock Sentinel
- **Description:** Detects live supply-chain disruptions near a place: cyclones, floods, earthquakes and severe weather, from GDACS and Open-Meteo.
- **Keywords:** supply chain, disruption, cyclone, flood, earthquake, GDACS, weather, risk, manufacturing
- **Example prompts:** see above.
