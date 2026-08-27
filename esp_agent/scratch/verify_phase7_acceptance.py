"""
Phase 7 LangGraph Architecture & Guideline Verification Acceptance Test Script
Store in scratch directory.
"""

import sys
import os
sys.path.insert(0, os.path.abspath("."))
import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from src.agent.supervisor.user_entry import UserEntryAdapter
from src.events.event_objective_router import EventObjectiveRouter
from shared.schemas.event import ESPEvent, SeverityLevel
from src.agent.supervisor.graph import supervisor_graph
from src.agent.supervisor.state import create_initial_agent_state
from src.agent.supervisor.checkpoint import CheckpointManager
from src.agent.objective_registry import ObjectiveRegistry
from src.policy.policy_engine import PolicyEngine
from src.tools.registry import OBJECTIVE_TOOL_ACL, ToolRegistry


def run_acceptance_audit():
    print("=" * 80)
    print("PHASE 7 LANGGRAPH ARCHITECTURE & GUIDELINE ACCEPTANCE AUDIT")
    print("=" * 80)

    results = {}

    # -------------------------------------------------------------------------
    # 1. VERIFY ENTRY POINTS CONVERGENCE
    # -------------------------------------------------------------------------
    print("\n--- [1] ENTRY POINTS CONVERGENCE TEST ---")
    user_adapter = UserEntryAdapter()
    event_router = EventObjectiveRouter()

    # User Entry: "Why is FS-031 producing less?"
    user_query = "Why is FS-031 producing less?"
    user_advisory = user_adapter.run(user_query=user_query, asset_id="FS-031", request_id="ACCEPT-USER-01")

    # Event Entry: PRODUCTION_DECLINE_DETECTED
    evt = ESPEvent(
        event_id="EVT-ACCEPT-01",
        event_type="PRODUCTION_DECLINE_DETECTED",
        severity=SeverityLevel.MEDIUM,
        asset_id="FS-031",
        source_service="telemetry_detector",
        payload={"telemetry": {"flow_rate": 1450.0, "pip": 350.0, "pdp": 2100.0}}
    )
    event_advisory = event_router.route_and_execute(evt)

    same_objective = (user_advisory.objective_id == event_advisory.objective_id == "OP02_PRODUCTION_DECLINE_RCA")
    same_asset = (user_advisory.asset_id == event_advisory.asset_id == "FS-031")
    user_provenance = user_advisory.provenance
    event_provenance = event_advisory.provenance

    print(f"User Request Objective ID : {user_advisory.objective_id}")
    print(f"Event Trigger Objective ID: {event_advisory.objective_id}")
    print(f"User Provenance           : {user_provenance}")
    print(f"Event Provenance          : {event_provenance}")
    
    assert same_objective, "User and Event entry points did not reach the same OP02 objective!"
    assert same_asset, "User and Event entry points targeted different assets!"
    results["1_entry_points"] = "PASS"

    # -------------------------------------------------------------------------
    # 2. VERIFY OBJECTIVE BINDING
    # -------------------------------------------------------------------------
    print("\n--- [2] OBJECTIVE BINDING & DEFINITION LOADING TEST ---")
    registry = ObjectiveRegistry()
    op02_def = registry.get("OP02_PRODUCTION_DECLINE_RCA")

    assert op02_def is not None, "ObjectiveRegistry failed to load OP02_PRODUCTION_DECLINE_RCA"
    print(f"Loaded Objective Title   : {op02_def.title}")
    print(f"Required Signals         : {op02_def.required_signals}")
    print(f"Allowed Specialists      : {op02_def.allowed_specialists}")
    print(f"Required Tools           : {op02_def.required_tools}")
    print(f"Safety Advisory Only     : {op02_def.safety.advisory_only}")
    results["2_objective_binding"] = "PASS"

    # -------------------------------------------------------------------------
    # 3. VERIFY AGENT STATE SCHEMA
    # -------------------------------------------------------------------------
    print("\n--- [3] UNIFIED STATE SCHEMA & CHECKPOINT TEST ---")
    test_state = create_initial_agent_state(run_id="RUN-STATE-TEST", asset_id="FS-031", objective_id="OP02_PRODUCTION_DECLINE_RCA")
    required_keys = ["run", "request", "context", "plan", "specialist_results", "evidence_refs", "conflicts", "safety_state", "advisory_draft", "audit", "budget", "error"]
    missing_keys = [k for k in required_keys if k not in test_state]

    assert not missing_keys, f"AgentState schema is missing keys: {missing_keys}"
    print(f"AgentState keys verified ({len(required_keys)}/12 sub-dicts present): {list(test_state.keys())}")

    # Checkpoint Test
    chk_mgr = CheckpointManager()
    chk_mgr.save_checkpoint(test_state)
    loaded_state = chk_mgr.load_checkpoint("RUN-STATE-TEST")
    assert loaded_state is not None and loaded_state["run"]["run_id"] == "RUN-STATE-TEST"
    print("Checkpoint save/load round-trip verified.")
    results["3_state_schema"] = "PASS"

    # -------------------------------------------------------------------------
    # 4. VERIFY SPECIALIST BOUNDARIES & ACL
    # -------------------------------------------------------------------------
    print("\n--- [4] SPECIALIST BOUNDARIES & TOOL ACL TEST ---")
    policy_engine = PolicyEngine(registry=registry)

    # Verify OP02 ACL
    op02_acl = OBJECTIVE_TOOL_ACL.get("OP02_PRODUCTION_DECLINE_RCA", set())
    print(f"OP02 Tool ACL: {op02_acl}")
    assert "calculate_operating_point" in op02_acl or "calculate_tdh" in op02_acl, "OP02 ACL missing required calculation tools!"

    # Verify RBAC enforcement
    rbac_pass = False
    try:
        policy_engine.enforce_specialist_rbac("OP02_PRODUCTION_DECLINE_RCA", "well_performance")
        rbac_pass = True
    except Exception as ex:
        print(f"RBAC check failed unexpectedly: {ex}")
    
    assert rbac_pass, "PolicyEngine rejected legitimate specialist 'well_performance' for OP02!"
    print("Specialist RBAC & Tool ACL gates verified.")
    results["4_specialist_boundaries"] = "PASS"

    # -------------------------------------------------------------------------
    # 5. VERIFY EVIDENCE & SAFETY GATES
    # -------------------------------------------------------------------------
    print("\n--- [5] EVIDENCE & SAFETY GATES TEST ---")
    print(f"User Advisory Evidence Items Count : {len(user_advisory.evidence)}")
    print(f"User Advisory Safety Constraints   : {user_advisory.constraints}")
    print(f"User Advisory Verification Checklist: {user_advisory.verification}")

    assert len(user_advisory.evidence) > 0, "User advisory generated without evidence items!"
    assert len(user_advisory.verification) > 0, "User advisory missing human operator verification checklist!"
    results["5_evidence_safety"] = "PASS"

    # -------------------------------------------------------------------------
    # 6. VERIFY AUDIT TRACE
    # -------------------------------------------------------------------------
    print("\n--- [6] FULL AUDIT TRACE RECONSTRUCTION TEST ---")
    invoked_state = supervisor_graph.invoke(test_state)
    audit_log = invoked_state["audit"]

    tool_call_steps = [t.get("step") for t in audit_log.get("tool_calls", [])]
    print(f"Supervisor Node Execution Trace Sequence:")
    for idx, tc in enumerate(audit_log.get("tool_calls", []), 1):
        print(f"  Step {idx:02d}: {tc.get('step')} -> {tc}")

    expected_nodes = ["resolve_objective", "resolve_asset", "data_quality_gate", "load_minimum_context", "plan", "delegate", "collect_results", "evidence_gate", "conflict_check", "safety_gate", "generate_advisory_draft"]
    for en in expected_nodes:
        assert en in tool_call_steps, f"Audit trace missing mandatory node execution: '{en}'"

    print("Complete end-to-end audit trace reconstructed successfully.")
    results["6_audit_trace"] = "PASS"

    # -------------------------------------------------------------------------
    # SUMMARY OF ACCEPTANCE AUDIT
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("PHASE 7 ACCEPTANCE TEST RESULTS SUMMARY")
    print("=" * 80)
    for k, v in results.items():
        print(f"  [{v}] {k}")
    print("=" * 80)


if __name__ == "__main__":
    run_acceptance_audit()
