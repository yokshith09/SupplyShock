"""M0: hello Orchestrator. Chat Protocol + mailbox; echoes the user's text."""
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

load_dotenv()

agent = Agent(
    name="supplyshock-orchestrator",
    seed=os.getenv("ORCH_SEED", "supplyshock-orchestrator-dev-seed"),
    port=int(os.getenv("ORCH_PORT", "8000")),
    mailbox=True,
    publish_agent_details=True,
)
chat = Protocol(spec=chat_protocol_spec)


def reply(text: str) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=text)],
    )


@chat.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id),
    )
    text = " ".join(c.text for c in msg.content if isinstance(c, TextContent)).strip()
    ctx.logger.info(f"chat from {sender}: {text!r}")
    if text:
        await ctx.send(sender, reply(f"SupplyShock online. You said: {text}"))


@chat.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(chat, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
