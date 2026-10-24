"""Sentinel agent: EventQuery -> EventResult, plus Chat Protocol. Owner: D2.

Run:  python -m agents.sentinel.agent
"""
import asyncio

from agents.d2_chat import sentinel_chat
from agents.d2_kit import build_agent
from agents.sentinel import service
from shared.models import EventQuery, EventResult

GDACS_REFRESH_S = 600

agent = build_agent(
    name="sentinel",
    seed_env="SENTINEL_SEED",
    port_env="SENTINEL_PORT",
    default_port=8101,
    description="Detects live supply-chain disruptions (cyclones, floods, earthquakes, severe weather) "
    "near a place using GDACS and Open-Meteo.",
    request_model=EventQuery,
    response_model=EventResult,
    handle=service.handle,
    chat_handler=sentinel_chat,
)


@agent.on_event("startup")
async def warm_gdacs(ctx):
    # GDACS can take 8-25 s; warm the cache in the background so start-up isn't blocked.
    asyncio.create_task(service.refresh_gdacs())


@agent.on_interval(period=GDACS_REFRESH_S)
async def refresh_gdacs(ctx):
    count = await service.refresh_gdacs()
    ctx.logger.info(f"GDACS refresh: {count} events" if count >= 0 else "GDACS refresh failed (keeping cache)")


if __name__ == "__main__":
    agent.run()
