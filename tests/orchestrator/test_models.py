from shared.models import Event, ExposureReport, GeoPoint, Option, ServiceError


def test_roundtrip():
    ev = Event(event_id="E1", type="cyclone", title="t", center=GeoPoint(lat=13.08, lon=80.27),
               radius_km=150, severity="HIGH", start="2026-10-24")
    assert Event.parse_raw(ev.json()) == ev
    r = ExposureReport(incident_id="i", task_id="T2")
    assert r.degraded is False and r.revenue_at_risk_inr == 0.0
    assert Option(option_id="OPT-C", label="x").actions == []
    assert ServiceError("TIMEOUT", "m", True).retryable
