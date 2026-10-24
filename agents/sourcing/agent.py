"""Sourcing agent: SourcingRequest -> SourcingResult, plus Chat Protocol. Owner: D2.

Run:  python -m agents.sourcing.agent
"""
from agents.d2_chat import sourcing_chat
from agents.d2_kit import build_agent
from agents.sourcing import service
from shared.models import SourcingRequest, SourcingResult

agent = build_agent(
    name="sourcing",
    seed_env="SOURCING_SEED",
    port_env="SOURCING_PORT",
    default_port=8103,
    description="Finds and ranks backup suppliers outside a disruption zone by price, lead time, quality and risk, widening the search when needed.",
    request_model=SourcingRequest,
    response_model=SourcingResult,
    handle=service.handle,
    chat_handler=sourcing_chat,
)

if __name__ == "__main__":
    agent.run()
