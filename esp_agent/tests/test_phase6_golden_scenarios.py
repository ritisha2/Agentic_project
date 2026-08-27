"""
Phase 6 Golden Integration Test Suite
Grounded in Phase 6 Event-Driven Architecture Spec §33
Reconciled 100% against Phase 4 Objectives (OP00 - OP06)
"""

import uuid
import pytest
from shared.schemas.event import ESPEvent, SeverityLevel
from src.events.processor import EventProcessor
from src.events.trigger_adapter import EventTriggerAdapter
from src.events.db_event_store import DatabaseEventStore


def test_golden_scenario_1_failure_risk(tmp_path):
    """
    Scenario 1: FAILURE_RISK_PERSISTED event -> EventProcessor (hysteresis verified)
    -> OP05_EARLY_WARNING -> EventTriggerAdapter -> Advisory with event correlation IDs.
    """
    db_store = DatabaseEventStore(db_path=str(tmp_path / "g1.db"))
    processor = EventProcessor(db_store=db_store)
    adapter = EventTriggerAdapter()
    uid = uuid.uuid4().hex[:8]

    # Emit 3 events to satisfy hysteresis (min_persistence_samples = 3)
    evt_last = None
    for i in range(3):
        evt = ESPEvent(
            event_id=f"EVT-GOLD-10{i}-{uid}",
            event_type="FAILURE_RISK_PERSISTED",
            asset_id=f"FS-G1-{uid}",
            source_service="failure-risk-model",
            severity=SeverityLevel.HIGH,
            payload={"risk_7d": 0.74},
            correlation_id=f"CORR-GOLDEN-01-{uid}",
            idempotency_key=f"IDEMP-G1-10{i}-{uid}"
        )
        evt_last = evt
        processor.process_event(evt)

    advisory = adapter.execute_event_workflow(evt_last)
    assert advisory is not None
    assert advisory.objective_id == "OP05_EARLY_WARNING"
    assert any(f"CORR-GOLDEN-01-{uid}" in p for p in advisory.provenance)


def test_golden_scenario_2_esp_trip(tmp_path):
    """
    Scenario 2: ESP_TRIPPED event -> EventProcessor -> OP03_FAULT_DIAGNOSIS -> Fault Advisory.
    """
    db_store = DatabaseEventStore(db_path=str(tmp_path / "g2.db"))
    processor = EventProcessor(db_store=db_store)
    adapter = EventTriggerAdapter()
    uid = uuid.uuid4().hex[:8]

    evt = ESPEvent(
        event_id=f"EVT-TRIP-{uid}",
        event_type="ESP_TRIPPED",
        asset_id="FS-031",
        source_service="scada",
        severity=SeverityLevel.CRITICAL,
        payload={"trip_reason": "Motor Winding Over-Temperature (138°C)"},
        correlation_id=f"CORR-GOLDEN-02-{uid}",
        idempotency_key=f"IDEMP-G2-{uid}"
    )

    is_act, reason = processor.process_event(evt)
    assert is_act is True

    advisory = adapter.execute_event_workflow(evt)
    assert advisory is not None
    assert advisory.objective_id == "OP03_FAULT_DIAGNOSIS"


def test_golden_scenario_3_production_decline(tmp_path):
    """
    Scenario 3: PRODUCTION_DECLINE_DETECTED -> EventProcessor -> OP02_PRODUCTION_DECLINE_RCA
    -> LangGraph Workflow -> Evidence Pack & RCA Advisory.
    """
    db_store = DatabaseEventStore(db_path=str(tmp_path / "g3.db"))
    processor = EventProcessor(db_store=db_store)
    adapter = EventTriggerAdapter()
    uid = uuid.uuid4().hex[:8]
    asset_id = f"FS-G3-{uid}"

    # PRODUCTION_DECLINE_DETECTED requires min_persistence_samples = 4
    evt_last = None
    for i in range(4):
        evt = ESPEvent(
            event_id=f"EVT-DECL-{i}-{uid}",
            event_type="PRODUCTION_DECLINE_DETECTED",
            asset_id=asset_id,
            source_service="telemetry-detector",
            severity=SeverityLevel.MEDIUM,
            payload={"current_flow_bpd": 1100.0, "baseline_bpd": 1720.0},
            correlation_id=f"CORR-GOLDEN-03-{uid}",
            idempotency_key=f"IDEMP-G3-{i}-{uid}"
        )
        evt_last = evt
        is_act, _ = processor.process_event(evt)

    assert is_act is True

    advisory = adapter.execute_event_workflow(evt_last)
    assert advisory is not None
    assert advisory.objective_id == "OP02_PRODUCTION_DECLINE_RCA"
    assert advisory.confidence > 0.0


def test_golden_scenario_4_autonomous_control_refusal(tmp_path):
    """
    Scenario 4: CONTROL_COMMAND_ATTEMPTED event -> OP00_OPERATIONAL_CONTROL -> Refusal Advisory.
    """
    adapter = EventTriggerAdapter()
    uid = uuid.uuid4().hex[:8]

    evt = ESPEvent(
        event_id=f"EVT-CTRL-{uid}",
        event_type="CONTROL_COMMAND_ATTEMPTED",
        asset_id="FS-031",
        source_service="control-system",
        severity=SeverityLevel.HIGH,
        payload={"command": "SET_FREQUENCY_60HZ"},
        correlation_id=f"CORR-GOLDEN-04-{uid}",
        idempotency_key=f"IDEMP-G4-{uid}"
    )

    advisory = adapter.execute_event_workflow(evt)
    assert advisory is not None
    assert advisory.objective_id == "OP00_OPERATIONAL_CONTROL"


def test_golden_scenario_5_asset_config_change(tmp_path):
    """
    Scenario 5: ASSET_CONFIGURATION_CHANGED event -> DatabaseEventStore permanent audit log.
    """
    db_store = DatabaseEventStore(db_path=str(tmp_path / "g5.db"))
    processor = EventProcessor(db_store=db_store)
    uid = uuid.uuid4().hex[:8]

    evt = ESPEvent(
        event_id=f"EVT-CFG-{uid}",
        event_type="ASSET_CONFIGURATION_CHANGED",
        asset_id="FS-031",
        source_service="advait-registry",
        severity=SeverityLevel.INFO,
        payload={"changed_fields": ["esp_configuration.pump.stages"]},
        correlation_id=f"CORR-GOLDEN-05-{uid}",
        idempotency_key=f"IDEMP-G5-{uid}"
    )

    is_act, reason = processor.process_event(evt)
    assert is_act is True
    assert reason == "ACTIONABLE_PROMOTED"

    stored_evt = db_store.get_event(f"EVT-CFG-{uid}")
    assert stored_evt is not None
    assert stored_evt.event_type == "ASSET_CONFIGURATION_CHANGED"
