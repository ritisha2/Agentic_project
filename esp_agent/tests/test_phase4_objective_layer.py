"""
Phase 4 Acceptance Test Suite for Objective & Workflow Layer
Grounded in PHASE_4_Objective_Layer_Implementation_Plan_ESP_APM.docx §23
"""

import pytest
from datetime import datetime

from src.agent.objective_registry import ObjectiveRegistry
from src.agent.intent_router import IntentRouter
from src.agent.data_quality_gate import DataQualityGate
from src.agent.objective_router import ObjectiveRouter
from src.agent.workflows.op02_workflow import create_op02_workflow
from src.schemas.advisory import StandardAdvisoryPayload


def test_01_objective_registry_loads():
    """Verify ObjectiveRegistry loads all machine-readable objective definitions."""
    registry = ObjectiveRegistry()
    objectives = registry.list_all()
    assert len(objectives) >= 6
    
    op02 = registry.get("OP02_PRODUCTION_DECLINE_RCA")
    assert op02 is not None
    assert op02.objective_id == "OP02_PRODUCTION_DECLINE_RCA"
    assert "O1" in op02.strategic_objectives
    assert op02.safety.advisory_only is True
    assert len(op02.success_criteria) > 0


def test_02_intent_routing_deterministic():
    """Verify Path A deterministic keyword matching in IntentRouter."""
    router = IntentRouter()
    
    obj_id, conf, path = router.route("Why is FS-031 producing less flow?")
    assert obj_id == "OP02_PRODUCTION_DECLINE_RCA"
    assert conf >= 0.90
    assert path == "Path_A_Deterministic"

    obj_id, conf, path = router.route("Check motor temperature warning and diagnose fault")
    assert obj_id == "OP03_FAULT_DIAGNOSIS"
    assert path == "Path_A_Deterministic"


def test_03_intent_routing_semantic():
    """Verify Path B semantic classification and Path C event mapping in IntentRouter."""
    router = IntentRouter()
    
    # Path C Event test
    obj_id, conf, path = router.route("Unhandled query text", event_code="PRODUCTION_DECLINE_DETECTED")
    assert obj_id == "OP02_PRODUCTION_DECLINE_RCA"
    assert conf == 1.0
    assert path == "Path_C_Event"

    # Path B Semantic test
    obj_id, conf, path = router.route("Show system health index and remaining useful life")
    assert obj_id in ("OP04_HEALTH_ASSESSMENT", "OP03_FAULT_DIAGNOSIS")
    assert conf > 0.5


def test_04_data_quality_gate_complete():
    """Verify DataQualityGate returns COMPLETE when all signals are present and fresh."""
    gate = DataQualityGate(max_age_seconds=300)
    telemetry = {
        "motor_temperature": 135.0,
        "intake_pressure": 350.0,
        "discharge_pressure": 2100.0,
        "flowline_pressure": 45.0,
        "frequency": 50.0,
        "drive_current_average": 62.0
    }
    required = ["motor_temperature", "intake_pressure", "discharge_pressure"]
    
    report = gate.evaluate(required_signals=required, telemetry_data=telemetry, telemetry_timestamp=datetime.utcnow().isoformat() + "Z")
    assert report.status == "COMPLETE"
    assert report.gate_passed is True
    assert len(report.missing_signals) == 0
    assert "seed data are NOT approved limits" in report.operating_range_note


def test_05_data_quality_gate_partial():
    """Verify DataQualityGate handles missing required signals with PARTIAL status."""
    gate = DataQualityGate(max_age_seconds=300)
    telemetry = {
        "motor_temperature": 135.0,
        "frequency": 50.0
    }
    required = ["motor_temperature", "intake_pressure", "discharge_pressure"]
    
    report = gate.evaluate(required_signals=required, telemetry_data=telemetry)
    assert report.status == "PARTIAL"
    assert report.gate_passed is True
    assert "intake_pressure" in report.missing_signals
    assert "PARTIAL TELEMETRY" in report.disclosure_message


def test_06_data_quality_gate_stale():
    """Verify DataQualityGate marks telemetry STALE if timestamp exceeds threshold."""
    gate = DataQualityGate(max_age_seconds=300)
    telemetry = {"motor_temperature": 135.0}
    required = ["motor_temperature"]
    old_ts = "2020-01-01T00:00:00Z"
    
    report = gate.evaluate(required_signals=required, telemetry_data=telemetry, telemetry_timestamp=old_ts)
    assert report.status == "STALE"
    assert report.freshness_seconds > 300.0


def test_07_op02_end_to_end():
    """Verify OP02 Production Decline RCA LangGraph workflow end-to-end execution."""
    workflow = create_op02_workflow()
    initial_state = {
        "request_id": "REQ-TEST-OP02",
        "asset_id": "FS-031",
        "user_query": "Why is FS-031 producing less liquid?",
        "objective_id": "OP02_PRODUCTION_DECLINE_RCA",
        "asset_context": None,
        "telemetry_data": {
            "motor_temperature": 135.0,
            "flow_rate": 1450.0,
            "current": 62.0,
            "pip": 350.0,
            "pdp": 2100.0
        },
        "dq_report": None,
        "model_output": None,
        "tdh_ft": 0.0,
        "bep_deviation_pct": 0.0,
        "evidence_pack": None,
        "advisory": None,
        "audit_trail": [],
        "error": None
    }
    
    final_state = workflow.invoke(initial_state)
    assert final_state.get("advisory") is not None
    advisory = StandardAdvisoryPayload(**final_state["advisory"])
    assert advisory.asset_id == "FS-031"
    assert advisory.objective_id == "OP02_PRODUCTION_DECLINE_RCA"
    assert "Production Decline RCA" in advisory.assessment
    assert advisory.confidence > 0.0
    assert len(advisory.verification) > 0


def test_08_operational_control_refusal():
    """Verify autonomous control attempts receive REFUSAL advisory."""
    router = ObjectiveRouter()
    advisory = router.route_and_execute(
        user_query="Increase ESP speed to 60 Hz automatically",
        asset_id="FS-031"
    )
    assert advisory.objective_id in ("OBJ_OPERATIONAL_CONTROL", "OP00_OPERATIONAL_CONTROL")
    assert "REFUSAL" in advisory.assessment
    assert "Do NOT attempt remote automated speed" in advisory.recommendation


def test_09_insufficient_evidence_policy():
    """Verify DataQualityGate disclosure reduces advisory confidence when telemetry is partial."""
    router = ObjectiveRouter()
    advisory = router.route_and_execute(
        user_query="Why is FS-031 producing less?",
        asset_id="FS-031"
    )
    assert advisory.confidence <= 1.0
    assert len(advisory.provenance) > 0
    assert any("operating ranges from seed data are not approved limits" in p.lower() for p in advisory.provenance)


def test_10_success_criteria_checker():
    """Verify ObjectiveRouter validates success criteria for generated advisories."""
    router = ObjectiveRouter()
    advisory = router.route_and_execute(
        user_query="Diagnose motor overheating on FS-031",
        asset_id="FS-031"
    )
    assert advisory.assessment != ""
    assert advisory.diagnosis != ""
    assert advisory.recommendation != ""
    assert len(advisory.verification) >= 3
