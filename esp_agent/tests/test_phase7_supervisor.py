"""
Unit Tests for Sprint 7.2: Supervisor Graph Skeleton and Visual Graph Export
Grounded in ESP_APM_PHASE_7_LangGraph_Supervisor_MultiAgent_Architecture_Design.docx §7, §9
"""

import pytest
from src.agent.supervisor.state import create_initial_agent_state
from src.agent.supervisor.graph import create_supervisor_graph, supervisor_graph


def test_01_supervisor_graph_compiles_and_runs():
    """Verify Supervisor graph compilation and end-to-end invocation."""
    graph = create_supervisor_graph()
    initial_state = create_initial_agent_state(
        run_id="RUN-SUP-01",
        asset_id="FS-031",
        user_query="Diagnose production decline on FS-031",
        objective_id="OP02_PRODUCTION_DECLINE_RCA"
    )

    final_state = graph.invoke(initial_state)

    assert final_state["run"]["status"] == "COMPLETED"
    assert final_state["advisory_draft"] is not None
    assert final_state["advisory_draft"]["asset_id"] == "FS-031"
    assert len(final_state["specialist_results"]) > 0


def test_02_supervisor_graph_delegation_loop():
    """Verify delegation loop visits all planned specialist steps."""
    initial_state = create_initial_agent_state(
        run_id="RUN-SUP-02",
        asset_id="FS-031",
        user_query="Why is production dropping?"
    )

    final_state = supervisor_graph.invoke(initial_state)
    results = final_state["specialist_results"]

    # Verify specialists in result list
    specialist_ids = [r["specialist_id"] for r in results]
    assert "well_performance" in specialist_ids
    assert "reliability" in specialist_ids
    assert "knowledge" in specialist_ids


def test_03_supervisor_graph_visual_export():
    """Verify LangGraph mermaid visual graph representation export."""
    mermaid_str = supervisor_graph.get_graph().draw_mermaid()
    assert "resolve_objective" in mermaid_str
    assert "delegate" in mermaid_str
    assert "generate_advisory_draft" in mermaid_str
    assert "-->" in mermaid_str
