from enum import Enum


class Intent(str, Enum):
    SCAN = "SCAN"
    EVENT_IMPACT = "EVENT_IMPACT"
    SUPPLIER_CHECK = "SUPPLIER_CHECK"
    SOURCE_ALT = "SOURCE_ALT"
    STATUS = "STATUS"
    HELP = "HELP"


class Severity(str, Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EventType(str, Enum):
    CYCLONE = "cyclone"
    FLOOD = "flood"
    EARTHQUAKE = "earthquake"
    WILDFIRE = "wildfire"
    STRIKE = "strike"
    PORT_CLOSURE = "port_closure"
    FIRE = "fire"
    SANCTION = "sanction"
    OTHER = "other"


class ActionType(str, Enum):
    RFQ_EMAIL = "rfq_email"
    EXPEDITE_EMAIL = "expedite_email"
    DRAFT_PO = "draft_po"
    CUSTOMER_NOTICE = "customer_notice"


class ErrorCode(str, Enum):
    TIMEOUT = "TIMEOUT"
    UPSTREAM_API = "UPSTREAM_API"
    NOT_FOUND = "NOT_FOUND"
    INVALID_INPUT = "INVALID_INPUT"
    INTERNAL = "INTERNAL"
