"""
Tests for ML Model Output Consumption & Integration Architecture
Grounded in dependency_detail.md & ESP_Agentic_ML_Team_Dependencies_and_API_PreRequisites.md
"""

import json
import pytest
from fastapi.testclient import TestClient

from src.schemas.contracts import MLContractV2Payload, TriggeredLimitPayload
from src.api.ml_model_mock_server import app as ml_app
from src.adapters.model_adapter import ModelAdapter
from src.agent.specialists.reliability import create_reliability_graph
from src.agent.supervisor.user_entry import UserEntryAdapter

ml_client = TestClient(ml_app)


def test_1_ml_contract_schema_validation():
    raw_json = {
        "asset_id": "FS-010",
        "well_id": "OPG-W010",
        "timestamp": 1787810015,
        "model_id": "esp-hybrid-dual-tier",
        "model_version": "v2.0.0",
        "feature_version": "phys-v2.1",
        "status": "VALID",
        "state": "FAULT",
        "fault_classification": "Bearing Degradation",
        "confidence_score": 0.969,
        "is_anomaly": True,
        "anomaly_score": 0.615,
        "contributors": ["R_MOTOR_TEMP", "R_VIBRATION_X"],
        "triggered_limits": [
            {"tag": "R_MOTOR_TEMP", "value": 115.0, "limit": 100.0, "type": "HIGH"},
            {"tag": "R_VIBRATION_X", "value": 0.48, "limit": 0.30, "type": "HIGH"},
        ],
        "telemetry_received": {"R_MOTOR_TEMP": 115.0, "R_VIBRATION_X": 0.48},
    }

    payload = MLContractV2Payload.model_validate(raw_json)
    assert payload.asset_id == "FS-010"
    assert payload.fault_classification == "Bearing Degradation"
    assert payload.confidence_score == 0.969
    assert len(payload.triggered_limits) == 2
    assert payload.triggered_limits[0].tag == "R_MOTOR_TEMP"


def test_2_ml_mock_api_endpoints():
    r_health = ml_client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["model_version"] == "v2.0.0"

    r_predict = ml_client.post("/api/v1/esps/FS-010/predict", json={})
    assert r_predict.status_code == 200
    data = r_predict.json()
    assert data["asset_id"] == "FS-010"
    assert data["fault_classification"] == "Bearing Degradation"
    assert data["confidence_score"] == 0.969

    r_hist = ml_client.get("/api/v1/esps/FS-010/history?range=6h")
    assert r_hist.status_code == 200
    assert r_hist.json()["history_count"] == 6


def test_3_model_adapter_v2_prediction():
    adapter = ModelAdapter(api_url="http://localhost:8082")

    # Offline asset fallback
    output = adapter.get_model_output("FS-031")
    assert output.asset_id == "FS-031"
    assert output.fault.predicted_fault_class is not None


def test_4_reliability_specialist_ml_consumption():
    graph = create_reliability_graph()
    state = {
        "input": {"asset_id": "FS-010"},
        "model_output": {},
        "rule_violations": [],
        "findings": [],
        "evidence_refs": [],
        "output": None,
    }

    res = graph.invoke(state)
    assert res["output"]["specialist_id"] == "reliability"
    findings_str = " ".join(res["output"]["findings"])
    assert "ML Predictive Diagnostic" in findings_str


def test_5_e2e_supervisor_ml_integration():
    entry = UserEntryAdapter()
    advisory = entry.run(
        user_query="Jane, perform reliability assessment for FS-010",
        asset_id="FS-010",
        request_id="REQ-ML-E2E-TEST",
    )

    assert advisory.asset_id == "FS-010"
    assert advisory.advisory_id == "ADV-REQ-ML-E2E-TEST"
    assert advisory.diagnosis is not None


def test_6_unavailable_sensor_telemetry_missing_handling():
    r_offline = ml_client.post("/api/v1/esps/FS-OFFLINE/predict", json={})
    assert r_offline.status_code == 200
    data = r_offline.json()
    assert data["status"] == "UNAVAILABLE"
    assert data["state"] == "DEGRADED"
    assert data["reason"] == "SENSOR_TELEMETRY_MISSING"
    assert data["confidence_score"] is None

