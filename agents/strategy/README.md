# SupplyShock Strategy

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

Turns a disruption's exposure into scored mitigation options (expedite, switch supplier, split) with extra cost, orders saved and a recommendation.

Part of **SupplyShock**, a multi-agent supply-chain disruption responder (Fetch-A-Thon 3.0). The SupplyShock Orchestrator calls this agent as one step of its plan; you can also chat with it directly in ASI:One.

## Example prompts
- "Cyclone near Chennai: what should we do?"
- "Mitigation options if Sriperumbudur floods"
- "Options for a cyclone on the Tamil Nadu coast"

## Interface
- Typed protocol `supplyshock-strategy-task`: `StrategyRequest` -> `StrategyOptions` (or `TaskError`). Models: `shared/models.py`.
- Agent Chat Protocol: plain-text questions, plain-text answers.

## Run and test on its own
```bash
pip install -r requirements.txt
python data/seed_generator.py        # ERP demo data (Exposure, Sourcing, Strategy)
python -m agents.strategy.agent        # prints the agent address and an Agentverse inspector link
pytest tests/strategy
```
Env vars: STRATEGY_SEED, STRATEGY_PORT (8104), DB_PATH, ASI1_API_KEY, STRATEGY_LLM, SEED_TODAY.

## Agentverse profile (copy into the agent page)
- **Title:** SupplyShock Strategy
- **Description:** Turns a disruption's exposure into scored mitigation options (expedite, switch supplier, split) with extra cost, orders saved and a recommendation.
- **Keywords:** supply chain, mitigation, strategy, procurement, risk, decision support, manufacturing
- **Example prompts:** see above.
