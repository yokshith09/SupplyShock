"""Standalone chat answers of D2's agents (agents/d2_chat.py)."""

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agents import d2_chat  # noqa: E402
from data import seed_generator  # noqa: E402
from shared.models import ServiceError  # noqa: E402


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    path = tmp_path / "supplyshock.db"
    seed_generator.build(path, today=date(2026, 10, 24))
    monkeypatch.setenv("DB_PATH", str(path))
    monkeypatch.setenv("SEED_TODAY", "2026-10-24")
    monkeypatch.setenv("REPLAY_MODE", "true")
    monkeypatch.setenv("STRATEGY_LLM", "false")


def test_place_and_type_parsing():
    assert d2_chat.place_from("Cyclone warning on the Tamil Nadu coast, are we exposed?") == "Tamil Nadu"
    assert d2_chat.place_from("Backup suppliers for M-12 near Chennai") == "Chennai"
    assert d2_chat.event_type("is there a typhoon near Shenzhen") == "cyclone"
    assert d2_chat.place_from("are we exposed?") is None


async def test_sentinel_chat_replay():
    answer = await d2_chat.sentinel_chat("Any disruptions near the Tamil Nadu coast?")
    assert "Cyclone Michaung" in answer and "0.86" in answer


async def test_exposure_chat_story_numbers():
    answer = await d2_chat.exposure_chat("Cyclone near Chennai, what is our exposure?")
    assert "3 suppliers hit" in answer and "12 orders" in answer and "₹1.82 Cr" in answer


async def test_sourcing_chat_by_name_without_place():
    answer = await d2_chat.sourcing_chat("Find alternates for ECU housing")
    assert "S-21" in answer and "S-14" in answer
    assert "S-03" not in answer and "M-05" not in answer


async def test_strategy_chat_recommends_c():
    answer = await d2_chat.strategy_chat("Cyclone near Chennai: what should we do?")
    assert "OPT-C" in answer and "(recommended)" in answer.split("OPT-C", 1)[1].split("\n", 1)[0]


async def test_unknown_place_raises_for_wrapper(monkeypatch):
    async def nowhere(_text, timeout_s=6):
        return None

    monkeypatch.setattr("agents.sentinel.service.geocode", nowhere)
    with pytest.raises(ServiceError):
        await d2_chat.sentinel_chat("any events near Atlantisville")
