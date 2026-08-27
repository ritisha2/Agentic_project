"""
Unit Tests for Sprint 7.9: Event Entry Path & EventObjectiveRouter Bridge
Grounded in ESP_APM_PHASE_7_LangGraph_Supervisor_MultiAgent_Architecture_Design.docx §8, §23, §24
"""

import pytest
from shared.schemas.event import ESPEvent, SeverityLevel
from src.events.event_objective_router import EventObjectiveRouter


def test_01_event_objective_router_production_decline():
    """Verify EventObjectiveRouter maps event to objective and triggers Supervisor execution."""
    router = EventObjectiveRouter()

    event = ESPEvent(
        event_id="EVT-1001",
        event_type="PRODUCTION_DECLINE_DETECTED",
        severity=SeverityLevel.MEDIUM,
        asset_id="FS-031",
        source_service="telemetry_detector",
        payload={"telemetry": {"flow_rate": 1450.0, "pip": 350.0, "pdp": 2100.0}}
    )

    advisory = router.route_and_execute(event)

    assert advisory is not None
    assert advisory.asset_id == "FS-031"
    assert advisory.objective_id == "OP02_PRODUCTION_DECLINE_RCA"
    assert any("Event ID:" in p for p in advisory.provenance)


def test_02_event_objective_router_trip():
    """Verify EventObjectiveRouter handles critical ESP_TRIPPED event."""
    router = EventObjectiveRouter()

    event = ESPEvent(
        event_id="EVT-1002",
        event_type="ESP_TRIPPED",
        severity=SeverityLevel.CRITICAL,
        asset_id="FS-031",
        source_service="scada_listener",
        payload={"telemetry": {"motor_temperature": 155.0}}
    )

    advisory = router.route_and_execute(event)

    assert advisory is not None
    assert advisory.objective_id == "OP03_FAULT_DIAGNOSIS"


def test_03_event_objective_router_unknown_event():
    """Verify EventObjectiveRouter gracefully handles unmapped event."""
    router = EventObjectiveRouter()

    event = ESPEvent(
        event_id="EVT-1003",
        event_type="UNKNOWN_CUSTOM_EVENT",
        severity=SeverityLevel.INFO,
        asset_id="FS-031",
        source_service="test"
    )

    advisory = router.route_and_execute(event)
    assert advisory is None
