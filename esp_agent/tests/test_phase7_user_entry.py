"""
Unit Tests for Sprint 7.10: User Entry Path & REST Gateway Supervisor Integration
Grounded in ESP_APM_PHASE_7_LangGraph_Supervisor_MultiAgent_Architecture_Design.docx §8, §24
"""

import pytest
from fastapi.testclient import TestClient

from src.agent.supervisor.user_entry import UserEntryAdapter
from src.api.rest.gateway import app

client = TestClient(app)


def test_01_user_entry_adapter_production_decline():
    """Verify UserEntryAdapter processes user query through Supervisor."""
    adapter = UserEntryAdapter()

    advisory = adapter.run(
        user_query="Why is FS-031 producing less flow?",
        asset_id="FS-031",
        request_id="REQ-USER-01"
    )

    assert advisory is not None
    assert advisory.asset_id == "FS-031"
    assert advisory.objective_id == "OP02_PRODUCTION_DECLINE_RCA"
    assert advisory.confidence >= 0.80
    assert len(advisory.provenance) > 0


def test_02_user_entry_adapter_fault_diagnosis():
    """Verify UserEntryAdapter processes fault diagnosis query."""
    adapter = UserEntryAdapter()

    advisory = adapter.run(
        user_query="Check high motor temperature on FS-031",
        asset_id="FS-031",
        request_id="REQ-USER-02"
    )

    assert advisory is not None
    assert advisory.objective_id == "OP03_FAULT_DIAGNOSIS"


def test_03_rest_gateway_agent_run_endpoint():
    """Verify POST /v1/agent/run endpoint end-to-end via FastAPI TestClient."""
    payload = {
        "user_query": "Why is FS-031 producing less flow?",
        "asset_id": "FS-031"
    }

    response = client.post("/v1/agent/run", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["meta"]["service"] == "supervisor_agent"
    assert data["data"]["asset_id"] == "FS-031"
    assert data["data"]["objective_id"] == "OP02_PRODUCTION_DECLINE_RCA"
