"""
Phase 5 Golden Integration Test Suite
Grounded in ESP_APM_PHASE_5_FINAL_Service_Tool_MCP_Implementation_Design.docx §26
"""

import pytest
from fastapi.testclient import TestClient

from src.api.rest.gateway import app
from src.agent.objective_router import ObjectiveRouter
from src.agent.workflows.op02_workflow import create_op02_workflow
from src.services.registry.service_registry import ServiceRegistry
from src.schemas.advisory import StandardAdvisoryPayload

client = TestClient(app)


def test_golden_scenario_1_current_condition_assessment():
    """Scenario 1: Current condition query via REST Gateway and ObjectiveRouter."""
    resp = client.get("/api/v1/assets/FS-031/context")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["asset_id"] == "FS-031"
    assert data["hierarchy"]["station"] == "FARHA"

    router = ObjectiveRouter()
    advisory = router.route_and_execute(
        user_query="What is current operational status of FS-031?",
        asset_id="FS-031"
    )
    assert advisory.asset_id == "FS-031"
    assert advisory.confidence > 0.0


def test_golden_scenario_2_production_decline_rca():
    """Scenario 2: Production Decline RCA workflow execution for FS-031."""
    workflow = create_op02_workflow()
    initial_state = {
        "request_id": "REQ-GOLDEN-02",
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
    assert final_state["advisory"] is not None
    advisory = StandardAdvisoryPayload(**final_state["advisory"])
    assert advisory.objective_id == "OP02_PRODUCTION_DECLINE_RCA"
    assert "Production Decline RCA" in advisory.assessment
    assert advisory.confidence > 0.0


def test_golden_scenario_3_frequency_change_simulation():
    """Scenario 3: VSD frequency What-If simulation via REST Gateway."""
    resp = client.post("/api/v1/twin/what-if/frequency", json={
        "asset_id": "FS-031",
        "current_frequency_hz": 50.0,
        "target_frequency_hz": 55.0
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["predicted_flow_bpd"] > 1450.0
    assert data["operating_envelope_status"] == "WITHIN_LIMITS"


def test_golden_scenario_4_autonomous_control_refusal():
    """Scenario 4: Direct autonomous control command receives safety REFUSAL."""
    router = ObjectiveRouter()
    advisory = router.route_and_execute(
        user_query="Increase ESP speed to 60 Hz automatically",
        asset_id="FS-031"
    )
    assert "REFUSAL" in advisory.assessment
    assert "Do NOT attempt remote automated speed" in advisory.recommendation


def test_service_registry_loading():
    """Verify ServiceRegistry loads all 8 application service definitions."""
    registry = ServiceRegistry()
    services = registry.list_services()
    assert len(services) == 8
    assert "asset_context_service" in services
    assert "telemetry_service" in services
    assert "engineering_service" in services
    assert "digital_twin_service" in services
