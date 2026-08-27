"""
End-to-End Golden Vertical Slice Acceptance Test Suite for Phase 9 Product Integration
Grounded in ESP_APM_PHASE_9_FRONTEND_BACKEND_PRODUCT_INTEGRATION_ARCHITECTURE.docx §34
"""

import pytest
from fastapi.testclient import TestClient
from src.api.rest.gateway import app

client = TestClient(app)


def test_golden_vertical_slice_fs031_advisory_flow():
    """
    End-to-End Golden Vertical Slice Acceptance Test:
    FS-031 Selection -> Workspace BFF Aggregation -> Query Entry -> LangGraph Supervisor Run -> Evidence Pack -> XAI Visual Stories -> Advisory -> Audit Trace
    """
    asset_id = "FS-031"

    # Step 1: UI fetches Asset Workspace payload
    ws_resp = client.get(f"/api/ui/assets/{asset_id}/workspace")
    assert ws_resp.status_code == 200
    ws_data = ws_resp.json()
    assert ws_data["status"] == "SUCCESS"
    assert ws_data["asset_id"] == asset_id
    assert ws_data["engineering"]["tdh_ft"] > 0

    # Step 2: Operator submits natural-language query via BFF
    query = "Why is FS-031 producing less?"
    run_resp = client.post(
        "/api/ui/agent/run",
        json={"user_query": query, "asset_id": asset_id}
    )
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["status"] == "COMPLETED"
    assert run_data["objective_id"] == "OP02_PRODUCTION_DECLINE_RCA"

    advisory = run_data["advisory"]
    assert advisory["asset_id"] == asset_id
    assert advisory["confidence"] > 0.5
    assert len(advisory["evidence"]) > 0
    assert len(advisory["verification"]) > 0

    # Step 3: UI polls run status
    run_id = run_data["run_id"]
    status_resp = client.get(f"/api/ui/runs/{run_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["current_milestone"] == "ADVISORY_READY"

    # Step 4: UI fetches Evidence Pack and XAI Visual Story payload
    ev_resp = client.get(f"/api/ui/runs/{run_id}/evidence")
    assert ev_resp.status_code == 200
    ev_data = ev_resp.json()
    
    pack = ev_data["evidence_pack"]
    assert pack["frozen"] is True
    assert pack["checksum"] is not None
    assert len(pack["items"]) >= 4

    xai = ev_data["xai_explanation"]
    assert xai["supporting_evidence_count"] >= 3
    assert len(xai["counterfactuals"]) > 0
    assert len(xai["visual_stories"]) >= 2
