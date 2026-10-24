"""Exposure agent: ExposureRequest -> ExposureReport, plus Chat Protocol. Owner: D2.

Run:  python -m agents.exposure.agent
"""
from agents.d2_chat import exposure_chat
from agents.d2_kit import build_agent
from agents.exposure import service
from shared.models import ExposureRequest, ExposureReport

agent = build_agent(
    name="exposure",
    seed_env="EXPOSURE_SEED",
    port_env="EXPOSURE_PORT",
    default_port=8102,
    description="Works out which suppliers, materials and customer orders a disruption puts at risk: stock-out dates, severity and revenue at risk.",
    request_model=ExposureRequest,
    response_model=ExposureReport,
    handle=service.handle,
    chat_handler=exposure_chat,
)

if __name__ == "__main__":
    agent.run()
