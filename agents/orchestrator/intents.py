"""Intent classification: optional ASI1 call first, keyword fallback always available."""
import asyncio
import json
import os
import re
import urllib.request
from dataclasses import dataclass, field

from agents.orchestrator.prompts import INTENT_SYSTEM_PROMPT
from shared.constants import EventType, Intent

ASI1_URL = "https://api.asi1.ai/v1/chat/completions"
ASI1_MODEL = os.getenv("ASI1_MODEL", "asi1")

# raw place -> location string the Sentinel can geocode
LOCATIONS = {
    "tamil nadu": "Chennai", "chennai": "Chennai", "ennore": "Chennai", "sriperumbudur": "Chennai",
    "pune": "Pune", "gujarat": "Gujarat", "mumbai": "Mumbai", "vizag": "Visakhapatnam",
    "visakhapatnam": "Visakhapatnam", "shenzhen": "Shenzhen", "penang": "Penang",
    "stuttgart": "Stuttgart", "monterrey": "Monterrey", "suez": "Suez", "red sea": "Red Sea",
}

EVENT_WORDS = {
    EventType.CYCLONE: ("cyclone", "hurricane", "typhoon", "storm"),
    EventType.FLOOD: ("flood", "flooding"),
    EventType.EARTHQUAKE: ("earthquake", "quake"),
    EventType.WILDFIRE: ("wildfire",),
    EventType.PORT_CLOSURE: ("port closure", "port closed", "port shut"),
    EventType.STRIKE: ("strike", "blockade"),
    EventType.FIRE: ("factory fire", "fire"),
    EventType.SANCTION: ("sanction", "export ban", "tariff"),
}


@dataclass
class IntentResult:
    intent: Intent
    location: str | None = None
    event_type: str | None = None
    supplier_id: str | None = None
    material: str | None = None
    source: str = "keywords"
    raw: dict = field(default_factory=dict)


def _entities(text: str) -> dict:
    t = text.lower()
    location = next((v for k, v in LOCATIONS.items() if k in t), None)
    event_type = next((et.value for et, words in EVENT_WORDS.items() if any(w in t for w in words)), None)
    m = re.search(r"\bS-?(\d{1,3})\b", text, re.I)
    supplier_id = f"S-{int(m.group(1)):02d}" if m else None
    mat = re.search(r"(?:for|of)\s+([a-z0-9][a-z0-9 \-]{2,40}?)(?:[.?!,]|$)", t)
    return {"location": location, "event_type": event_type, "supplier_id": supplier_id,
            "material": mat.group(1).strip() if mat else None}


def classify_keywords(text: str) -> IntentResult:
    t = text.lower().strip()
    ent = _entities(text)
    if re.search(r"\b(update|status|any news|follow.?up)\b", t):
        intent = Intent.STATUS
    elif ent["supplier_id"] or re.search(r"\bsupplier\b.*\b(safe|risk|ok|okay|reliable)\b", t):
        intent = Intent.SUPPLIER_CHECK
    elif re.search(r"\b(backup|alternate|alternative|alternates|replacement|source|sourcing)\b", t):
        intent = Intent.SOURCE_ALT
    elif ent["event_type"] or ent["location"]:
        intent = Intent.EVENT_IMPACT
    elif re.search(r"\b(exposed|exposure|risk|scan|anything|disruption)\b", t):
        intent = Intent.SCAN
    else:
        intent = Intent.HELP
    return IntentResult(intent=intent, source="keywords", **ent)


def _call_asi1(text: str, api_key: str, timeout_s: float) -> dict:
    body = json.dumps({
        "model": ASI1_MODEL,
        "messages": [{"role": "system", "content": INTENT_SYSTEM_PROMPT},
                     {"role": "user", "content": text}],
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(ASI1_URL, data=body, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        content = json.loads(resp.read())["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", content, re.S)
    return json.loads(m.group(0))


async def classify(text: str, timeout_s: float = 8.0) -> IntentResult:
    key = os.getenv("ASI1_API_KEY", "").strip()
    if key:
        try:
            d = await asyncio.wait_for(asyncio.to_thread(_call_asi1, text, key, timeout_s), timeout_s + 1)
            kw = _entities(text)
            return IntentResult(
                intent=Intent(d["intent"]),
                location=d.get("location") or kw["location"],
                event_type=d.get("event_type") or kw["event_type"],
                supplier_id=d.get("supplier_id") or kw["supplier_id"],
                material=d.get("material") or kw["material"],
                source="asi1", raw=d)
        except Exception:  # any failure -> keyword fallback
            pass
    return classify_keywords(text)
