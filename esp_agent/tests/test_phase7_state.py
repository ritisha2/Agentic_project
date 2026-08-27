"""
Unit Tests for Sprint 7.1: AgentState, Specialist Contracts, and CheckpointManager
Grounded in ESP_APM_PHASE_7_LangGraph_Supervisor_MultiAgent_Architecture_Design.docx §6, §10, §18
"""

import pytest
from src.agent.supervisor.state import AgentState, create_initial_agent_state
from src.agent.supervisor.specialist_contracts import SpecialistInput, SpecialistOutput, ConflictRecord
from src.agent.supervisor.checkpoint import CheckpointManager


def test_01_agent_state_creation():
    """Verify initial AgentState structure and TypedDict schema compliance."""
    state = create_initial_agent_state(
        run_id="RUN-1001",
        asset_id="FS-031",
        user_query="Why is flow rate low?",
        objective_id="OP02_PRODUCTION_DECLINE_RCA"
    )

    assert state["run"]["run_id"] == "RUN-1001"
    assert state["run"]["objective_id"] == "OP02_PRODUCTION_DECLINE_RCA"
    assert state["run"]["trigger_type"] == "user"
    assert state["request"]["asset_id"] == "FS-031"
    assert state["request"]["user_query"] == "Why is flow rate low?"
    assert state["budget"]["max_steps"] == 20
    assert state["safety_state"]["is_safe"] is True
    assert isinstance(state["specialist_results"], list)


def test_02_specialist_input_output_schemas():
    """Verify SpecialistInput and SpecialistOutput Pydantic serialization."""
    spec_in = SpecialistInput(
        run_id="RUN-1001",
        objective_id="OP02_PRODUCTION_DECLINE_RCA",
        asset_id="FS-031",
        task="Evaluate pump head vs BEP curve",
        allowed_tools=["calculate_tdh", "get_live_snapshot"]
    )
    assert spec_in.run_id == "RUN-1001"
    assert "calculate_tdh" in spec_in.allowed_tools

    spec_out = SpecialistOutput(
        specialist_id="well_performance",
        status="complete",
        findings=["Pump operating 18% below BEP flow rate"],
        evidence_refs=["esp:telemetry:flow_rate:1450"],
        completion_reason="BEP deviation calculated successfully"
    )
    assert spec_out.specialist_id == "well_performance"
    assert spec_out.status == "complete"
    assert len(spec_out.findings) == 1


def test_03_conflict_record_schema():
    """Verify ConflictRecord data contract."""
    conflict = ConflictRecord(
        conflict_type="engineering_vs_ml",
        specialist_a="well_performance",
        specialist_b="reliability",
        description="Well performance shows gas lock, reliability shows bearing wear"
    )
    assert conflict.conflict_type == "engineering_vs_ml"
    assert conflict.resolution is None


def test_04_checkpoint_manager_roundtrip():
    """Verify CheckpointManager save, load, and clear operations."""
    mgr = CheckpointManager()
    state = create_initial_agent_state(run_id="RUN-CHECKPOINT-1", asset_id="FS-031")
    state["plan"]["steps"] = ["well_performance", "reliability"]

    # Save
    assert mgr.save_checkpoint(state) is True

    # Load
    loaded = mgr.load_checkpoint("RUN-CHECKPOINT-1")
    assert loaded is not None
    assert loaded["run"]["run_id"] == "RUN-CHECKPOINT-1"
    assert loaded["plan"]["steps"] == ["well_performance", "reliability"]

    # Clear
    mgr.clear_checkpoint("RUN-CHECKPOINT-1")
    loaded_after = mgr.load_checkpoint("RUN-CHECKPOINT-1")
    assert loaded_after is None
