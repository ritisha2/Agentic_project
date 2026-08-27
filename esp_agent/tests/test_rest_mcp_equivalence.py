"""
REST vs MCP Equivalence Test Suite
Grounded in ESP_APM_PHASE_5_FINAL_Service_Tool_MCP_Implementation_Design.docx §15, §25
"""

import pytest
from fastapi.testclient import TestClient
from src.api.rest.gateway import app
from src.api.mcp.engineering_mcp import mcp_calculate_tdh, mcp_calculate_bep

client = TestClient(app)


def test_tdh_rest_mcp_equivalence():
    """Verify calculate_tdh produces identical business results over REST and MCP."""
    pdp, pip, sg = 2100.0, 350.0, 1.0

    # REST Gateway call
    rest_resp = client.post("/api/v1/engineering/tdh", json={"pdp_psi": pdp, "pip_psi": pip, "fluid_sg": sg})
    assert rest_resp.status_code == 200
    rest_data = rest_resp.json()["data"]

    # MCP Tool call
    mcp_data = mcp_calculate_tdh(pdp_psi=pdp, pip_psi=pip, fluid_sg=sg)

    # Equivalence Assertion
    assert rest_data["tdh_ft"] == mcp_data["tdh_ft"]
    assert rest_data["delta_p_psi"] == mcp_data["delta_p_psi"]
    assert rest_data["unit"] == mcp_data["unit"]


def test_bep_rest_mcp_equivalence():
    """Verify calculate_bep produces identical business results over REST and MCP."""
    flow, target = 1450.0, 1750.0

    # REST Gateway call
    rest_resp = client.post("/api/v1/engineering/bep", json={"current_flow_bpd": flow, "bep_target_bpd": target})
    assert rest_resp.status_code == 200
    rest_data = rest_resp.json()["data"]

    # MCP Tool call
    mcp_data = mcp_calculate_bep(current_flow_bpd=flow, bep_target_bpd=target)

    # Equivalence Assertion
    assert rest_data["deviation_bpd"] == mcp_data["deviation_bpd"]
    assert rest_data["deviation_pct"] == mcp_data["deviation_pct"]
    assert rest_data["operating_region"] == mcp_data["operating_region"]
