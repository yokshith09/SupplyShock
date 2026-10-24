"""SupplyShock Orchestrator: the only agent users talk to (Chat Protocol + Interactive Cards).

All conversation logic lives in handler.Orchestrator; this file is transport only.
Env for the demo: DISPATCH_MODE=mock + DISPATCH_LOCAL_AGENTS=sentinel,exposure,action, REPLAY_MODE=true,
DEMO_SUPPLIER_INBOX + email settings (see .env.example). Seed the DB first: python data/seed_generator.py
"""
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)

load_dotenv()

from agents.orchestrator.cards import to_chat_message  # noqa: E402
from agents.orchestrator.handler import Orchestrator  # noqa: E402

agent = Agent(
    name="supplyshock-orchestrator",
    seed=os.getenv("ORCH_SEED", "supplyshock-orchestrator-dev-seed"),
    port=int(os.getenv("ORCH_PORT", "8000")),
    mailbox=True,
    publish_agent_details=True,
)
chat = Protocol(spec=chat_protocol_spec)
brain = Orchestrator()


@chat.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(timezone.utc),
                                               acknowledged_msg_id=msg.msg_id))
    text = " ".join(c.text for c in msg.content if isinstance(c, TextContent)).strip()
    if not text:  # StartSession / metadata-only messages
        if any(isinstance(c, StartSessionContent) for c in msg.content):
            await ctx.send(sender, to_chat_message(next(iter(await brain.on_text(sender, "help")))))
        return
    ctx.logger.info(f"chat from {sender[:14]}...: {text[:120]!r}")
    for reply in await brain.on_text(sender, text):
        await ctx.send(sender, to_chat_message(reply))


@chat.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(chat, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
