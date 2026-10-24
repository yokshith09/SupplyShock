INTENT_SYSTEM_PROMPT = """You classify messages sent to a supply-chain disruption assistant.
Return ONLY a JSON object with these keys:
  intent: one of SCAN, EVENT_IMPACT, SUPPLIER_CHECK, SOURCE_ALT, STATUS, HELP
  location: string or null (place named in the message)
  event_type: one of cyclone, flood, earthquake, wildfire, strike, port_closure, fire, sanction, other, or null
  supplier_id: string like S-07 or null
  material: string or null
Definitions:
  SCAN = "are we exposed to anything right now" with no specific event or place
  EVENT_IMPACT = a specific event or place and a question about exposure
  SUPPLIER_CHECK = is one supplier safe / risky
  SOURCE_ALT = find a backup or alternate supplier for a material
  STATUS = update on an earlier incident
  HELP = greeting or what can you do
No prose, no markdown."""

HELP_TEXT = (
    "SupplyShock online. I watch for supply-chain disruptions and tell you which suppliers, "
    "materials and customer orders are exposed.\n\n"
    "Try:\n"
    "- Cyclone warning on the Tamil Nadu coast, are we exposed?\n"
    "- Is supplier S-07 safe right now?\n"
    "- Find a backup supplier for ECU housings."
)
