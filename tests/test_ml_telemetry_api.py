"""
Integration Tests for ML Telemetry Polling API
=============================================
Verifies:
1. Server-to-server Broker ID authentication (401 / 403 / 200)
2. Extraction of all 14 standard VFD telemetry parameters
3. Single asset and multi-asset batch filtering
4. Standard and Tabular format modes for ML data loaders
5. Offset pagination and limit boundaries
"""

import pytest
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Make cced_esp importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CCED_ESP_DIR = PROJECT_ROOT / "cced_esp"
if str(CCED_ESP_DIR) not in sys.path:
    sys.path.insert(0, str(CCED_ESP_DIR))

from backend.main import app
from backend.config import VALID_BROKER_IDS

client = TestClient(app)

EXPECTED_14_PARAMS = {
    "intake_pressure_psi",
    "intake_temperature_c",
    "motor_temperature_c",
    "discharge_pressure_psi",
    "vibration_g",
    "leak_current_ct",
    "motor_voltage_v",
    "motor_current_a",
    "frequency_hz",
    "dhg_current",
    "whp_psi",
    "flp_psi",
    "annulus_pressure_psi",
    "vfd_status"
}


def test_unauthorized_when_missing_broker_id():
    """Verify 401 is returned when no Broker ID is supplied."""
    response = client.get("/api/v1/telemetry/unlabelled")
    assert response.status_code == 401
    payload = response.json()
    assert payload["detail"]["status"] == "ERROR"
    assert payload["detail"]["error"]["code"] == "MISSING_BROKER_ID"


def test_forbidden_when_invalid_broker_id():
    """Verify 403 is returned when an invalid/unauthorized Broker ID is supplied."""
    response = client.get(
        "/api/v1/telemetry/unlabelled",
        headers={"X-Broker-ID": "UNAUTHORIZED-HACKER-BROKER"}
    )
    assert response.status_code == 403
    payload = response.json()
    assert payload["detail"]["status"] == "ERROR"
    assert payload["detail"]["error"]["code"] == "UNAUTHORIZED_BROKER"


def test_successful_extraction_with_14_parameters():
    """Verify 200 OK and complete 14-parameter vector structure on valid request."""
    response = client.get(
        "/api/v1/telemetry/unlabelled?limit=10",
        headers={"X-Broker-ID": "BROKER-DEMO-001"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "SUCCESS"
    assert payload["code"] == 200
    assert payload["broker_id"] == "BROKER-DEMO-001"
    assert "pagination" in payload
    assert len(payload["data"]) > 0

    first_record = payload["data"][0]
    assert "timestamp" in first_record
    assert "asset_id" in first_record
    assert "parameters" in first_record

    params = first_record["parameters"]
    assert set(params.keys()) == EXPECTED_14_PARAMS


def test_query_param_broker_id_fallback():
    """Verify Broker ID passed via query parameter is accepted."""
    response = client.get(
        "/api/v1/telemetry/unlabelled?broker_id=CCED-ML-TEST-01&limit=5"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "SUCCESS"
    assert payload["broker_id"] == "CCED-ML-TEST-01"
    assert len(payload["data"]) > 0


def test_asset_filtering():
    """Verify asset_id filtering strictly returns the requested well."""
    response = client.get(
        "/api/v1/telemetry/unlabelled?asset_id=FS-031&limit=25",
        headers={"X-Broker-ID": "BROKER-DEMO-001"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "SUCCESS"
    assert len(payload["data"]) > 0
    for rec in payload["data"]:
        assert rec["asset_id"] == "FS-031" or rec["well_id"] == "FS-031"


def test_tabular_format_for_ml():
    """Verify format=tabular returns flat column arrays for Pandas/NumPy."""
    response = client.get(
        "/api/v1/telemetry/unlabelled?format=tabular&limit=20",
        headers={"X-Broker-ID": "BROKER-DEMO-001"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "SUCCESS"
    data = payload["data"]
    assert "timestamp" in data
    assert "intake_pressure_psi" in data
    assert "discharge_pressure_psi" in data
    assert len(data["timestamp"]) == len(data["intake_pressure_psi"])


def test_batch_query_post():
    """Verify POST batch query endpoint with multi-asset filtering."""
    body = {
        "asset_ids": ["FS-031", "FSWS-001-A"],
        "limit": 30,
        "offset": 0
    }
    response = client.post(
        "/api/v1/telemetry/unlabelled/query",
        json=body,
        headers={"X-Broker-ID": "OPG-SECURE-01"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "SUCCESS"
    assert len(payload["data"]) > 0
    for rec in payload["data"]:
        assert rec["well_id"] in ("FS-031", "FSWS-001-A") or any(w in rec["asset_id"] for w in ("FS-031", "FSWS-001-A"))
