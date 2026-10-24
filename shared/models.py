"""Message contracts (TRD section 5, envelope rules 04_TEAM_PLAN E.1).

Owner: D1. After Phase 0 changes are additive only (new optional fields with defaults).
Every request/response carries incident_id + task_id; every response has degraded + notes.
Money fields end in _inr, distances _km, durations _days/_s.
"""
from uagents import Model


class GeoPoint(Model):
    lat: float
    lon: float


class Event(Model):
    event_id: str
    type: str
    title: str
    center: GeoPoint
    radius_km: float
    severity: str
    start: str
    end: str | None = None
    sources: list[str] = []
    confidence: float = 0.0


class EventQuery(Model):
    incident_id: str
    task_id: str
    location: str | None = None
    type: str | None = None
    horizon_days: int = 7


class EventResult(Model):
    incident_id: str
    task_id: str
    events: list[Event] = []
    degraded: bool = False
    notes: str = ""


class MaterialExposure(Model):
    material_id: str
    name: str
    supplier_ids: list[str] = []
    cover_days: float
    stockout_date: str | None = None
    severity: str


class ExposureRequest(Model):
    incident_id: str
    task_id: str
    event: Event


class ExposureReport(Model):
    incident_id: str
    task_id: str
    suppliers_hit: list[str] = []
    materials: list[MaterialExposure] = []
    orders_at_risk: list[str] = []
    revenue_at_risk_inr: float = 0.0
    trace: list[str] = []
    degraded: bool = False
    notes: str = ""


class Alternate(Model):
    supplier_id: str
    name: str
    material_id: str
    price_inr: float
    lead_time_days: int
    distance_km: float
    score: float


class SourcingRequest(Model):
    incident_id: str
    task_id: str
    material_ids: list[str]
    exclude_zone: Event


class SourcingResult(Model):
    incident_id: str
    task_id: str
    alternates: list[Alternate] = []
    search_radius_km: float = 0.0
    degraded: bool = False
    notes: str = ""


class Option(Model):
    option_id: str
    label: str
    actions: list[dict] = []
    cost_delta_inr: float = 0.0
    risk_reduction: float = 0.0
    orders_saved: int = 0
    recommended: bool = False
    rationale: str = ""


class StrategyRequest(Model):
    incident_id: str
    task_id: str
    exposure: ExposureReport
    sourcing: SourcingResult


class StrategyOptions(Model):
    incident_id: str
    task_id: str
    options: list[Option] = []
    degraded: bool = False
    notes: str = ""


class ActionRequest(Model):
    incident_id: str
    task_id: str
    option: Option
    approved_by: str


class ActionResult(Model):
    type: str
    target: str
    status: str  # "done" | "failed" | "draft"
    detail: str = ""


class ActionReceipt(Model):
    incident_id: str
    task_id: str
    results: list[ActionResult] = []
    degraded: bool = False
    notes: str = ""


class WatchSubscribe(Model):
    incident_id: str
    task_id: str = ""
    event: Event
    user_sender: str
    interval_min: int = 30


class WatchAlert(Model):
    incident_id: str
    task_id: str = ""
    change: str
    new_severity: str


class TaskError(Model):
    incident_id: str
    task_id: str
    code: str
    message: str
    retryable: bool = False


class ServiceError(Exception):
    """Raised by a specialist service; the agent wrapper turns it into TaskError."""

    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code, self.message, self.retryable = code, message, retryable
