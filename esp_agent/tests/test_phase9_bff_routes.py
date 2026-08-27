"""
Unit Test Suite for Backend-for-Frontend (BFF) API Routes (Step 2)
"""

import pytest
from fastapi.testclient import TestClient
from src.api.rest.gateway import app

client = TestClient(app)


def test_1_bff_asset_workspace_endpoint():
    resp = client.get("/api/ui/assets/FS-031/workspace")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["asset_id"] == "FS-031"
    assert "telemetry" in data
    assert "engineering" in data


def test_2_bff_asset_timeline_endpoint():
    resp = client.get("/api/ui/assets/FS-031/timeline")
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_id"] == "FS-031"
    assert len(data["events"]) >= 1


def test_3_bff_agent_run_endpoint():
    resp = client.post(
        "/api/ui/agent/run",
        json={"user_query": "Why is FS-031 producing less?", "asset_id": "FS-031"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert "run_id" in data
    assert "advisory" in data


def test_4_bff_run_evidence_endpoint():
    # Run agent first to generate evidence
    client.post(
        "/api/ui/agent/run",
        json={"user_query": "Why is FS-031 producing less?", "asset_id": "FS-031"}
    )

    resp = client.get("/api/ui/runs/RUN-TEST-01/evidence")
    assert resp.status_code == 200
    data = resp.json()
    assert "evidence_pack" in data
    assert "xai_explanation" in data
