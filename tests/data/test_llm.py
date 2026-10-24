import sys
from pathlib import Path

import httpx
import pytest
import respx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared import llm  # noqa: E402

URL = "https://api.asi1.ai/v1/chat/completions"
MSGS = [{"role": "user", "content": "classify: cyclone near Chennai"}]


def reply(text: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("ASI1_API_KEY", "test-key")
    monkeypatch.delenv("ASI1_MODEL", raising=False)
    monkeypatch.delenv("ASI1_BASE_URL", raising=False)


@pytest.mark.asyncio
@respx.mock
async def test_complete_success_sends_model_and_auth():
    route = respx.post(URL).mock(return_value=reply("hello"))
    assert await llm.complete(MSGS) == "hello"
    sent = route.calls.last.request
    assert sent.headers["Authorization"] == "Bearer test-key"
    assert b'"model":"asi1-mini"' in sent.content.replace(b" ", b"")


@pytest.mark.asyncio
@respx.mock
async def test_complete_json_strips_fences():
    respx.post(URL).mock(return_value=reply('```json\n{"intent": "EVENT_IMPACT"}\n```'))
    assert await llm.complete_json(MSGS, schema_hint='{"intent": "..."}') == {"intent": "EVENT_IMPACT"}


@pytest.mark.asyncio
@respx.mock
async def test_complete_json_retries_once_on_invalid_json():
    route = respx.post(URL).mock(side_effect=[reply("sure, here you go"), reply('{"intent": "SCAN"}')])
    assert await llm.complete_json(MSGS, schema_hint="{}") == {"intent": "SCAN"}
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_complete_json_gives_up_after_second_invalid_reply():
    respx.post(URL).mock(return_value=reply("not json"))
    with pytest.raises(llm.LLMError):
        await llm.complete_json(MSGS, schema_hint="{}")


@pytest.mark.asyncio
@respx.mock
async def test_retries_on_500_then_succeeds():
    route = respx.post(URL).mock(side_effect=[httpx.Response(500), reply("ok")])
    assert await llm.complete(MSGS) == "ok"
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_4xx_is_not_retried():
    route = respx.post(URL).mock(return_value=httpx.Response(401, text="bad key"))
    with pytest.raises(llm.LLMError):
        await llm.complete(MSGS)
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("ASI1_API_KEY")
    with pytest.raises(llm.LLMError, match="ASI1_API_KEY"):
        await llm.complete(MSGS)


@pytest.mark.asyncio
@respx.mock
async def test_api_key_not_in_error_message():
    respx.post(URL).mock(return_value=httpx.Response(403, text="forbidden"))
    with pytest.raises(llm.LLMError) as exc:
        await llm.complete(MSGS)
    assert "test-key" not in str(exc.value)
