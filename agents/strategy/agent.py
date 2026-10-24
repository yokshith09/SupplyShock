"""Strategy agent: StrategyRequest -> StrategyOptions, plus Chat Protocol. Owner: D2.

Run:  python -m agents.strategy.agent
"""
from agents.d2_chat import strategy_chat
from agents.d2_kit import build_agent
from agents.strategy import service
from shared.models import StrategyRequest, StrategyOptions

agent = build_agent(
    name="strategy",
    seed_env="STRATEGY_SEED",
    port_env="STRATEGY_PORT",
    default_port=8104,
    description="Turns a disruption's exposure into scored mitigation options (expedite, switch, split) with costs, orders saved and a recommendation.",
    request_model=StrategyRequest,
    response_model=StrategyOptions,
    handle=service.handle,
    chat_handler=strategy_chat,
)

if __name__ == "__main__":
    agent.run()
