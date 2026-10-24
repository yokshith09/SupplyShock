"""Dispatch switch: DISPATCH_MODE = mock | local | remote. Owner: D1.

mock   -> load the matching response JSON from fixtures and copy incident_id/task_id from the request
local  -> (M2) import agents.<agent>.service and await handle(request)
remote -> (M5) ctx.send to the agent address in config/agents.json
"""
import asyncio
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


def _mode() -> str:
    return os.getenv("DISPATCH_MODE", "mock").lower()


def _load_fixture(model_cls) -> dict:
    for d in FIXTURE_DIRS:
        p = d / f"{model_cls.__name__}.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"no fixture for {model_cls.__name__} in {[str(d) for d in FIXTURE_DIRS]}")


async def call(agent: str, request, timeout_s: float = 20):
    if agent not in RESPONSE_MODEL:
        raise ValueError(f"unknown agent '{agent}'")
    mode = _mode()
    if mode == "mock":
        return await asyncio.wait_for(_mock(agent, request), timeout_s)
    if mode == "local":
        raise NotImplementedError("DISPATCH_MODE=local is added in milestone M2")
    if mode == "remote":
        raise NotImplementedError("DISPATCH_MODE=remote is added in milestone M5")
    raise ValueError(f"bad DISPATCH_MODE '{mode}' (use mock, local or remote)")


async def _mock(agent: str, request):
    cls = RESPONSE_MODEL[agent]
    data = _load_fixture(cls)
    data["incident_id"] = request.incident_id
    data["task_id"] = request.task_id
    return cls.parse_obj(data)
