"""Action agent: executes approved options (RFQ/expedite emails, draft PO, customer notices).

Typed protocol for the Orchestrator (ActionRequest -> ActionReceipt) plus the Chat Protocol so the
agent is discoverable on its own. The Orchestrator is the one that talks to users.
"""
import os
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    chat_protocol_spec,
)

from agents.action.service import handle
from shared.models import ActionReceipt, ActionRequest, ServiceError, TaskError

load_dotenv()

agent = Agent(
    name="supplyshock-action",
    seed=os.getenv("ACTION_SEED", "supplyshock-action-dev-seed"),
    port=int(os.getenv("ACTION_PORT", "8001")),
    mailbox=True,
    publish_agent_details=True,
)

task = Protocol(name="supplyshock-action-task", version="0.1.0")
chat = Protocol(spec=chat_protocol_spec)


@task.on_message(ActionRequest, replies={ActionReceipt, TaskError})
async def on_action(ctx: Context, sender: str, msg: ActionRequest):
    ctx.logger.info(f"ActionRequest {msg.incident_id}/{msg.task_id} option={msg.option.option_id}")
    try:
        receipt = await handle(msg)
        await ctx.send(sender, receipt)
    except ServiceError as e:
        await ctx.send(sender, TaskError(incident_id=msg.incident_id, task_id=msg.task_id,
                                         code=e.code, message=e.message, retryable=e.retryable))
    except Exception as e:  # noqa: BLE001
        await ctx.send(sender, TaskError(incident_id=msg.incident_id, task_id=msg.task_id,
                                         code="INTERNAL", message=repr(e), retryable=False))


@chat.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(timezone.utc),
                                               acknowledged_msg_id=msg.msg_id))
    text = ("I am the SupplyShock Action agent. I send RFQ and expedite requests, draft purchase orders and "
            "customer notices, but only after a plan is approved. To start, ask the SupplyShock "
            "Orchestrator, for example: 'Cyclone warning on the Tamil Nadu coast, are we exposed?'")
    await ctx.send(sender, ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(),
                                       content=[TextContent(type="text", text=text)]))


@chat.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(task)
agent.include(chat, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
