"""
Unit Tests for Sprint 7.3: Well Performance and Reliability Specialist Subgraphs
Grounded in ESP_APM_PHASE_7_LangGraph_Supervisor_MultiAgent_Architecture_Design.docx §4, §10, §11
"""

import pytest
from src.agent.specialists.well_performance import well_performance_graph
from src.agent.specialists.reliability import reliability_graph
from src.agent.supervisor.state import create_initial_agent_state
from src.agent.supervisor.graph import create_supervisor_graph


def test_01_well_performance_subgraph_invocation():
    """Verify direct invocation of WellPerformanceGraph."""
    spec_input = {
        "run_id": "RUN-WP-01",
        "objective_id": "OP02_PRODUCTION_DECLINE_RCA",
        "asset_id": "FS-031",
        "task": "Evaluate pump hydraulic head",
        "policy_context": {"telemetry": {"flow_rate": 1450.0, "pip": 350.0, "pdp": 2100.0}}
    }

    res = well_performance_graph.invoke({
        "input": spec_input,
        "telemetry": {},
        "tdh_ft": 0.0,
        "bep_deviation_pct": 0.0,
        "findings": [],
        "evidence_refs": [],
        "output": None
    })

    output = res["output"]
    assert output is not None
    assert output["specialist_id"] == "well_performance"
    assert output["status"] == "complete"
    assert any("Best Efficiency Point" in f for f in output["findings"])
    assert any("esp:engineering:tdh" in ref for ref in output["evidence_refs"])


def test_02_reliability_subgraph_invocation():
    """Verify direct invocation of ReliabilityGraph."""
    spec_input = {
        "run_id": "RUN-REL-01",
        "objective_id": "OP03_FAULT_DIAGNOSIS",
        "asset_id": "FS-031",
        "task": "Assess failure risk and model output",
        "policy_context": {"telemetry": {"motor_temperature": 135.0}}
    }

    res = reliability_graph.invoke({
        "input": spec_input,
        "model_output": {},
        "rule_violations": [],
        "findings": [],
        "evidence_refs": [],
        "output": None
    })

    output = res["output"]
    assert output is not None
    assert output["specialist_id"] == "reliability"
    assert output["status"] == "complete"
    assert any("Predictive Diagnostic" in f for f in output["findings"])
    assert any("esp:model" in ref for ref in output["evidence_refs"])


def test_03_supervisor_integrates_specialist_outputs():
    """Verify Supervisor invokes specialist subgraphs and aggregates findings into advisory."""
    graph = create_supervisor_graph()
    initial_state = create_initial_agent_state(
        run_id="RUN-INTEG-01",
        asset_id="FS-031",
        user_query="Why is FS-031 producing less flow?",
        objective_id="OP02_PRODUCTION_DECLINE_RCA"
    )

    final_state = graph.invoke(initial_state)

    results = final_state["specialist_results"]
    assert len(results) >= 2
    
    specialist_ids = [r["specialist_id"] for r in results]
    assert "well_performance" in specialist_ids
    assert "reliability" in specialist_ids

    # Check advisory diagnosis contains specialist findings
    diagnosis = final_state["advisory_draft"]["diagnosis"]
    assert "Best Efficiency Point" in diagnosis or "Predictive Diagnostic" in diagnosis
