"""Shared uAgents wrapper for D2's specialist agents (Sentinel, Exposure, Sourcing, Strategy). Owner: D2.

Each agent gets:
  - a typed task protocol: Request -> service.handle() -> Response (ServiceError -> TaskError)
  - the Agent Chat Protocol, so it is discoverable and usable on its own in ASI:One
  - mailbox=True, its README as the Agentverse profile, and its address logged on start-up
"""

from __future__ import annotations

import os
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from uagents import Agent, Context, Model, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

from shared.constants import ErrorCode
from shared.models import ServiceError, TaskError

load_dotenv()

ChatHandler = Callable[[str], Awaitable[str]]


def text_reply(text: str, end_session: bool = False) -> ChatMessage:
    content = [TextContent(type="text", text=text)]
    if end_session:
        content.append(EndSessionContent(type="end-session"))
    return ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(), content=content)


def build_agent(
    *,
    name: str,
    seed_env: str,
    port_env: str,
    default_port: int,
    description: str,
    request_model: type[Model],
    response_model: type[Model],
    handle: Callable[[Model], Awaitable[Model]],
    chat_handler: ChatHandler,
) -> Agent:
    folder = Path(__file__).resolve().parent / name
    agent = Agent(
        name=f"supplyshock-{name}",
        seed=os.getenv(seed_env, f"supplyshock-{name}-dev-seed"),
        port=int(os.getenv(port_env, str(default_port))),
        mailbox=True,
        publish_agent_details=True,
        readme_path=str(folder / "README.md"),
        description=description,
    )

    task = Protocol(name=f"supplyshock-{name}-task", version="0.1.0")
    chat = Protocol(spec=chat_protocol_spec)

    @task.on_message(request_model, replies={response_model, TaskError})
    async def on_task(ctx: Context, sender: str, msg: Model) -> None:
        started = time.perf_counter()
        try:
            response = await handle(msg)
        except ServiceError as exc:
            response = TaskError(
                incident_id=msg.incident_id, task_id=msg.task_id,
                code=exc.code, message=exc.message, retryable=exc.retryable,
            )
        except Exception as exc:  # noqa: BLE001 - never let a task crash the agent
            ctx.logger.exception(f"{name} task failed")
            response = TaskError(
                incident_id=msg.incident_id, task_id=msg.task_id,
                code=ErrorCode.INTERNAL.value, message=f"{name} failed: {exc!r}", retryable=True,
            )
        latency_ms = round((time.perf_counter() - started) * 1000)
        ctx.logger.info(
            f"{request_model.__name__} incident_id={msg.incident_id} task_id={msg.task_id} "
            f"-> {type(response).__name__} latency_ms={latency_ms}"
        )
        await ctx.send(sender, response)

    @chat.on_message(ChatMessage)
    async def on_chat(ctx: Context, sender: str, msg: ChatMessage) -> None:
        await ctx.send(
            sender,
            ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id),
        )
        text = " ".join(c.text for c in msg.content if isinstance(c, TextContent)).strip()
        if not text:
            return
        try:
            answer = await chat_handler(text)
        except ServiceError as exc:
            answer = exc.message
        except Exception as exc:  # noqa: BLE001
            ctx.logger.exception(f"{name} chat failed")
            answer = f"Sorry, something went wrong on my side ({type(exc).__name__}). Please try again."
        await ctx.send(sender, text_reply(answer))

    @chat.on_message(ChatAcknowledgement)
    async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement) -> None:
        pass

    @agent.on_event("startup")
    async def announce(ctx: Context) -> None:
        ctx.logger.info(f"supplyshock-{name} address: {agent.address}")

    agent.include(task, publish_manifest=True)
    agent.include(chat, publish_manifest=True)
    return agent
