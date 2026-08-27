"""
Tests for ESP Telemetry Mock API Service (esp-telemetry-api :8081)
Grounded in ESP_APM_Telemetry_Mock_API_Specification.docx §19
"""

import pytest
from fastapi.testclient import TestClient

from src.api.telemetry_mock_server import app

client = TestClient(app)


def test_1_system_endpoints():
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "UP"

    r_ready = client.get("/readiness")
    assert r_ready.status_code == 200
    assert r_ready.json()["status"] == "READY"

    r_ver = client.get("/version")
    assert r_ver.status_code == 200
    assert r_ver.json()["service"] == "esp-telemetry-api"


def test_2_get_current_telemetry_fs031():
    resp = client.get("/api/v1/assets/FS-031/telemetry/current")
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_id"] == "FS-031"
    assert data["well_id"] == "FS-031"
    assert "liquid_rate" in data["measurements"]
    assert data["measurements"]["liquid_rate"]["value"] == 735.7
    assert data["measurements"]["liquid_rate"]["unit"] == "BPD"
    assert data["measurements"]["intake_pressure"]["value"] == 236.5
    assert data["measurements"]["intake_pressure"]["unit"] == "psi"
    assert data["quality"]["overall"] == "GOOD"


def test_3_telemetry_ingestion():
    payload = {
        "asset_id": "FS-032",
        "well_id": "FS-032",
        "timestamp": "2026-08-27T10:00:00.000Z",
        "state": "running",
        "measurements": {
            "liquid_rate": 820.5,
            "intake_pressure": 250.0,
            "discharge_pressure": 1950.0,
            "frequency": 50.0,
            "motor_current": 20.1,
            "motor_voltage": 1020.0,
            "motor_temperature": 82.3,
            "vibration_rms": 0.12,
            "voltage_imbalance": 0.5,
            "current_imbalance": 0.8,
        },
    }
    r_ingest = client.post("/api/v1/telemetry", json=payload)
    assert r_ingest.status_code == 201
    assert r_ingest.json()["status"] == "SUCCESS"

    r_get = client.get("/api/v1/assets/FS-032/telemetry/current")
    assert r_get.status_code == 200
    data = r_get.json()
    assert data["asset_id"] == "FS-032"
    assert data["measurements"]["liquid_rate"]["value"] == 820.5
    assert data["measurements"]["liquid_rate"]["unit"] == "BPD"


def test_4_get_historical_telemetry():
    resp = client.get("/api/v1/assets/FS-031/telemetry/history?signals=liquid_rate,intake_pressure")
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_id"] == "FS-031"
    assert "history" in data
    assert len(data["history"]) >= 1


def test_5_get_telemetry_trend():
    resp = client.get("/api/v1/assets/FS-031/telemetry/trend?signals=liquid_rate,intake_pressure")
    assert resp.status_code == 200
    data = resp.json()
    assert "trends" in data
    assert "liquid_rate" in data["trends"]
    assert data["trends"]["liquid_rate"]["unit"] == "BPD"


def test_6_get_telemetry_quality_and_schema():
    r_qod = client.get("/api/v1/assets/FS-031/telemetry/quality")
    assert r_qod.status_code == 200
    assert r_qod.json()["quality"]["overall"] == "GOOD"

    r_schema = client.get("/api/v1/assets/FS-031/telemetry/schema")
    assert r_schema.status_code == 200
    assert "liquid_rate" in r_schema.json()["canonical_signals"]


def test_7_ground_truth_isolation():
    r_gt = client.get("/api/v1/test/assets/FS-031/ground-truth")
    assert r_gt.status_code == 200
    assert r_gt.json()["is_test_fixture"] is True


def test_8_error_handling_unknown_asset():
    resp = client.get("/api/v1/assets/UNKNOWN-999/telemetry/current")
    assert resp.status_code == 404
    assert "NOT_FOUND" in resp.json()["detail"]
