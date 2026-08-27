"""
Phase 7 Golden Scenarios Integration Test Suite
Grounded in ESP_APM_PHASE_7_LangGraph_Supervisor_MultiAgent_Architecture_Design.docx §29
"""

import pytest
from shared.schemas.event import ESPEvent, SeverityLevel
from src.agent.supervisor.user_entry import UserEntryAdapter
from src.events.event_objective_router import EventObjectiveRouter


def test_golden_scenario_1_production_decline_rca():
    """Golden Scenario 1: User asks why flow rate dropped -> OP02 -> Well Performance + Reliability + Knowledge."""
    adapter = UserEntryAdapter()
    advisory = adapter.run(
        user_query="Why is FS-031 producing less flow?",
        asset_id="FS-031",
        request_id="GOLDEN-01"
    )

    assert advisory.asset_id == "FS-031"
    assert advisory.objective_id == "OP02_PRODUCTION_DECLINE_RCA"
    assert advisory.confidence >= 0.80
    assert "Best Efficiency Point" in advisory.diagnosis or "Predictive Diagnostic" in advisory.diagnosis
    assert len(advisory.verification) > 0


def test_golden_scenario_2_trip_rca():
    """Golden Scenario 2: Event ESP_TRIPPED -> OP03 -> Reliability + Knowledge."""
    router = EventObjectiveRouter()
    event = ESPEvent(
        event_id="EVT-TRIP-01",
        event_type="ESP_TRIPPED",
        severity=SeverityLevel.CRITICAL,
        asset_id="FS-031",
        source_service="scada_listener",
        payload={"telemetry": {"motor_temperature": 155.0}}
    )

    advisory = router.route_and_execute(event)

    assert advisory is not None
    assert advisory.objective_id == "OP03_FAULT_DIAGNOSIS"
    assert advisory.asset_id == "FS-031"
    assert any("Event ID:" in p for p in advisory.provenance)


def test_golden_scenario_3_frequency_whatif():
    """Golden Scenario 3: User asks what if frequency is increased -> Digital Twin scenario evaluation."""
    adapter = UserEntryAdapter()
    advisory = adapter.run(
        user_query="Predict impact of frequency increase to 62 Hz",
        asset_id="FS-031",
        request_id="GOLDEN-03"
    )

    assert advisory.asset_id == "FS-031"
    assert advisory.objective_id in ("OP00_OPERATIONAL_CONTROL", "OP05_EARLY_WARNING", "OP03_FAULT_DIAGNOSIS", "OP02_PRODUCTION_DECLINE_RCA")
    assert len(advisory.evidence) > 0


def test_golden_scenario_4_thermal_overheating():
    """Golden Scenario 4: User reports motor overheating -> OP03 -> Reliability fault diagnosis."""
    adapter = UserEntryAdapter()
    advisory = adapter.run(
        user_query="Check motor temperature warning and diagnose fault",
        asset_id="FS-031",
        request_id="GOLDEN-04"
    )

    assert advisory.objective_id == "OP03_FAULT_DIAGNOSIS"
    assert advisory.asset_id == "FS-031"


def test_golden_scenario_5_procedure_lookup():
    """Golden Scenario 5: User queries ESP startup procedure -> OP06 -> Knowledge specialist."""
    adapter = UserEntryAdapter()
    advisory = adapter.run(
        user_query="Search procedure for low intake pressure troubleshooting",
        asset_id="FS-031",
        request_id="GOLDEN-05"
    )

    assert advisory.asset_id == "FS-031"
    assert advisory.objective_id == "OP06_PROCEDURE_LOOKUP"


def test_golden_scenario_6_failure_risk_event():
    """Golden Scenario 6: Event FAILURE_RISK_INCREASED -> OP05 Early Warning -> Supervisor."""
    router = EventObjectiveRouter()
    event = ESPEvent(
        event_id="EVT-RISK-01",
        event_type="FAILURE_RISK_INCREASED",
        severity=SeverityLevel.HIGH,
        asset_id="FS-031",
        source_service="model_producer",
        payload={"risk_7d": 0.85}
    )

    advisory = router.route_and_execute(event)

    assert advisory is not None
    assert advisory.objective_id == "OP05_EARLY_WARNING"
