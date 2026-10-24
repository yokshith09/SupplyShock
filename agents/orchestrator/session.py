"""Per-sender conversation state. In-memory for now; get/save is the only interface used,
so it can move to agent storage later without touching callers."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Session:
    sender: str
    incident_id: str | None = None
    plan: Any = None
    plan_state: str = "RECEIVED"  # RECEIVED | PLANNED | RUNNING | AWAITING_APPROVAL | EXECUTING | CLOSED
    event: Any = None
    exposure: Any = None
    sourcing: Any = None
    options: list = field(default_factory=list)
    chosen_option_id: str | None = None
    receipt: Any = None


class SessionStore:
    def __init__(self) -> None:
        self._data: dict[str, Session] = {}

    def get(self, sender: str) -> Session:
        if sender not in self._data:
            self._data[sender] = Session(sender=sender)
        return self._data[sender]

    def save(self, session: Session) -> None:
        self._data[session.sender] = session

    def reset(self, sender: str) -> Session:
        self._data.pop(sender, None)
        return self.get(sender)
