"""Dispatch switch. Owner: D1.

DISPATCH_MODE = mock | local | remote   (default mock)
DISPATCH_LOCAL_AGENTS = comma list (e.g. "sentinel,exposure"): in mock mode these agents run their real
service in-process while the others stay on fixtures. Lets D2's services be plugged in one at a time.

mock   -> load the matching response JSON from fixtures; copy incident_id/task_id from the request
local  -> import agents.<agent>.service and await handle(request); ServiceError -> TaskError
remote -> (M5) ctx.send to the agent address in config/agents.json
"""
import asyncio
import importlib
import json
import os
from pathlib import Path

from shared import models

ROOT = Path(__file__).resolve().parents[1]
# D2's fixtures are preferred once merged; D1's copies keep the d1 branch self-contained.
FIXTURE_DIRS = [ROOT / "tests" / "fixtures" / "contracts", ROOT / "tests" / "orchestrator" / "fixtures"]

RESPONSE_MODEL = {
    "sentinel": models.EventResult,
    "exposure": models.ExposureReport,
    "sourcing": models.SourcingResult,
    "strategy": models.StrategyOptions,
    "action": models.ActionReceipt,
}


def mode_for(agent: str) -> str:
    mode = os.getenv("DISPATCH_MODE", "mock").lower()
    local = {a.strip() for a in os.getenv("DISPATCH_LOCAL_AGENTS", "").split(",") if a.strip()}
    if mode == "mock" and agent in local:
        return "local"
    return mode


def _load_fixture(model_cls) -> dict:
    for d in FIXTURE_DIRS:
        p = d / f"{model_cls.__name__}.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"no fixture for {model_cls.__name__} in {[str(d) for d in FIXTURE_DIRS]}")


async def call(agent: str, request, timeout_s: float = 20):
    if agent not in RESPONSE_MODEL:
        raise ValueError(f"unknown agent '{agent}'")
    mode = mode_for(agent)
    if mode == "mock":
        return await asyncio.wait_for(_mock(agent, request), timeout_s)
    if mode == "local":
        return await asyncio.wait_for(_local(agent, request), timeout_s)
    if mode == "remote":
        raise NotImplementedError("DISPATCH_MODE=remote is added in milestone M5")
    raise ValueError(f"bad DISPATCH_MODE '{mode}' (use mock, local or remote)")


async def _mock(agent: str, request):
    cls = RESPONSE_MODEL[agent]
    data = _load_fixture(cls)
    data["incident_id"] = request.incident_id
    data["task_id"] = request.task_id
    return cls.parse_obj(data)


async def _local(agent: str, request):
    try:
        service = importlib.import_module(f"agents.{agent}.service")
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            f"local dispatch needs agents/{agent}/service.py (not on this branch yet): {e}") from e
    try:
        return await service.handle(request)
    except models.ServiceError as e:
        return models.TaskError(incident_id=request.incident_id, task_id=request.task_id,
                                code=e.code, message=e.message, retryable=e.retryable)
