"""
Integration tests for EventTriggerAdapter (Event -> LangGraph workflow)
Grounded in Phase 6 Event-Driven Architecture Spec §12, §27
"""

import pytest
from shared.schemas.event import ESPEvent, SeverityLevel
from src.events.trigger_adapter import EventTriggerAdapter


def test_event_trigger_adapter_execution():
    """Verify EventTriggerAdapter executes OP02 workflow for PRODUCTION_DECLINE_DETECTED event."""
    adapter = EventTriggerAdapter()

    evt = ESPEvent(
        event_id="EVT-TRIG-001",
        event_type="PRODUCTION_DECLINE_DETECTED",
        asset_id="FS-031",
        source_service="telemetry-detector",
        severity=SeverityLevel.MEDIUM,
        payload={"drop_pct": 21.5, "target_objective_id": "OP02_PRODUCTION_DECLINE_RCA"},
        correlation_id="CORR-TRIG-001"
    )

    advisory = adapter.execute_event_workflow(evt)
    assert advisory is not None
    assert advisory.asset_id == "FS-031"
    assert advisory.objective_id == "OP02_PRODUCTION_DECLINE_RCA"
    assert any("EVT-TRIG-001" in p for p in advisory.provenance)
