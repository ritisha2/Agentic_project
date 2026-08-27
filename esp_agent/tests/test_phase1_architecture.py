"""
Phase 1 Architecture Freeze Integration Test Suite
Tests API contracts, model adapters, tool ACL gates, objective routing, and standard advisory output.
"""

import pytest
from src.schemas.contracts import (
    AssetContextPayload, TelemetryPayload, ModelOutputPayload,
    RuleStatusPayload, AnomalyResultPayload, FailurePredictionPayload,
    FaultDiagnosisPayload, HealthIndexPayload
)
from src.schemas.advisory import StandardAdvisoryPayload
from src.adapters.model_adapter import ModelAdapter
from src.adapters.asset_service import AssetService
from src.tools.registry import ToolRegistry, OBJECTIVE_TOOL_ACL
from src.agent.objective_router import ObjectiveRouter
from src.api.fastapi_app import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_1_external_contracts_serialization():
    asset = AssetContextPayload(
        asset_id="ESP-Well-001",
        well_id="WELL-001",
        pump_model="DN1750",
        motor_rating_hp=250.0
    )
    assert asset.asset_id == "ESP-Well-001"
    assert asset.pump_model == "DN1750"

def test_2_model_adapter_mock_fallback():
    adapter = ModelAdapter()
    output: ModelOutputPayload = adapter.get_model_output("ESP-Well-001", {"primary_thermal_metric": 135.0})
    
    assert output.asset_id == "ESP-Well-001"
    assert output.fault.predicted_fault_class == "MOTOR_OVERHEATING"
    assert output.fault.confidence == 0.87
    assert output.anomaly.anomaly_score == 0.91
    assert output.failure.risk_24h == 0.72
    assert output.health.health_index == 45

def test_3_asset_service_cache():
    service = AssetService()
    asset = service.get_asset("ESP-Well-001")
    assert asset.asset_id == "ESP-Well-001"
    assert asset.pump_model == "Weatherford DN1750"
    assert asset.be_point_bpd == 1750.0

def test_4_tool_registry_acl_enforcement():
    registry = ToolRegistry()
    registry.register_tool("get_live_snapshot", lambda **kw: "live_data")
    
    # Allowed under OBJ_DIAGNOSE_FAULT
    res = registry.execute_tool("get_live_snapshot", objective_id="OBJ_DIAGNOSE_FAULT")
    assert res == "live_data"
    
    # Forbidden under OBJ_OPERATIONAL_CONTROL
    with pytest.raises(PermissionError):
        registry.execute_tool("get_live_snapshot", objective_id="OBJ_OPERATIONAL_CONTROL")

def test_5_objective_router_9_step_handling():
    router = ObjectiveRouter()
    advisory: StandardAdvisoryPayload = router.route_and_execute(
        user_query="Why is ESP-Well-001 motor temperature high?",
        asset_id="ESP-Well-001"
    )
    
    assert advisory.asset_id == "ESP-Well-001"
    assert advisory.objective_id in ["OBJ_DIAGNOSE_FAULT", "OP03_FAULT_DIAGNOSIS", "OBJ_EXPLAIN_ALERT", "OBJ_TELEMETRY_ANALYSIS"]
    assert ("MOTOR_OVERHEATING" in advisory.diagnosis or "NORMAL_OPERATION" in advisory.diagnosis)
    assert advisory.confidence > 0.0
    assert len(advisory.evidence) > 0
    assert len(advisory.verification) >= 3
    assert len(advisory.constraints) > 0

def test_6_fastapi_advisory_endpoint():
    resp = client.post("/advisory", json={
        "user_query": "Check asset status and health",
        "asset_id": "ESP-Well-001",
        "kb_id": "esp"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_id"] == "ESP-Well-001"
    assert "assessment" in data
    assert "recommendation" in data
    assert "confidence" in data
