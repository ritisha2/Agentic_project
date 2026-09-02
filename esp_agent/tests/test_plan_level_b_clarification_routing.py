"""
Level B verification suite — Real conversation with a non-technical operator
Grounded in Plan.md §LEVEL B (Phases B1-B4)

Run with:
    .venv\\Scripts\\python.exe -m pytest tests/test_plan_level_b_clarification_routing.py -v

Like the Level A suite, these tests target code that does not exist yet as of writing.
Each class maps 1:1 to a Plan.md phase; tests skip with a clear reason if their phase's
prerequisite hasn't landed, rather than reporting false failures on unstarted work.

IMPORTANT: Level B depends on Level A (conversation_context plumbing) and specifically
B3 (clarification node) depends on B1 (checkpointer on the graph) per LangGraph's HITL
requirements. If B1 isn't done, B3 tests will skip rather than fail confusingly.
"""

import uuid
import inspect
import importlib
import pytest


# ---------------------------------------------------------------------------
# Phase B1 — Checkpointer wired onto the supervisor graph (HITL prerequisite)
# ---------------------------------------------------------------------------

class TestPhaseB1_GraphCheckpointer:
    """Plan.md B1.T1/B1.T2 — supervisor graph must compile WITH a checkpointer."""

    def test_graph_compiled_with_checkpointer(self):
        """
        B1.T1 — LangGraph interrupt()/resume and cross-turn state are impossible without
        a checkpointer at compile time. This inspects the compiled graph object for
        checkpointer wiring rather than assuming it from source text.
        """
        from src.agent.supervisor import graph as graph_mod
        compiled = graph_mod.supervisor_graph

        # CompiledGraph exposes .checkpointer when compiled with one; None otherwise.
        checkpointer = getattr(compiled, "checkpointer", None)
        assert checkpointer is not None, (
            "supervisor_graph must be compiled with a checkpointer (graph.compile(checkpointer=...)) "
            "for HITL clarification (Phase B3) to be possible at all. Currently compiles with none."
        )

    def test_graph_invoke_accepts_thread_id_config(self):
        """B1.T1 — invoking with a stable thread_id must not raise, proving checkpointer plumbing."""
        from src.agent.supervisor import graph as graph_mod
        from src.agent.supervisor.state import create_initial_agent_state

        compiled = graph_mod.supervisor_graph
        if getattr(compiled, "checkpointer", None) is None:
            pytest.skip("Checkpointer not wired yet (Phase B1.T1) — thread_id config is meaningless without it.")

        thread_id = f"TEST-THREAD-{uuid.uuid4().hex[:8]}"
        initial_state = create_initial_agent_state(
            run_id="LEVELB-B1-TEST",
            asset_id="FSWS-001-A",
            user_query="status check",
            objective_id="OP01_CURRENT_STATUS",
            trigger_type="user",
        )
        # Must accept a RunnableConfig with thread_id without raising
        try:
            compiled.invoke(initial_state, config={"configurable": {"thread_id": thread_id}})
        except Exception as ex:
            pytest.fail(f"Graph invoke with thread_id config raised: {ex}")

    def test_pause_resume_across_same_thread_id(self):
        """
        B1.T2 — verify a run can pause and resume against the same thread_id.
        Requires an actual interrupt()-emitting node to exist (Phase B3), so this
        test is the integration proof point for B1+B3 together.
        """
        from src.agent.supervisor import graph as graph_mod
        compiled = graph_mod.supervisor_graph
        if getattr(compiled, "checkpointer", None) is None:
            pytest.skip("Checkpointer not wired yet (Phase B1.T1).")
        if not hasattr(graph_mod, "clarification_node"):
            pytest.skip("clarification_node not implemented yet (Phase B3) — nothing to pause on.")
        pytest.skip(
            "Full pause/resume integration test requires a concrete ambiguous scenario "
            "from Phase B2+B3; implement alongside those phases rather than stubbing "
            "assertions against not-yet-defined interrupt payload shape."
        )


# ---------------------------------------------------------------------------
# Phase B2 — Ambiguity scoring in the router
# ---------------------------------------------------------------------------

class TestPhaseB2_AmbiguityScoring:
    """Plan.md B2.T1/B2.T2 — route() must return a real ambiguity signal."""

    def setup_method(self):
        from src.agent.intent_router import IntentRouter
        self.router = IntentRouter()

    def test_route_result_has_ambiguity_signal(self):
        """
        B2.T1 — route() must stop ALWAYS returning a confident objective. Accept either a
        richer return type (RouteResult with is_ambiguous) or a 4-tuple; this test checks
        for whichever the implementation lands on, without over-prescribing the shape.
        """
        result = self.router.route("is everything okay?")
        has_ambiguity_field = False
        if hasattr(result, "is_ambiguous"):
            has_ambiguity_field = True
        elif isinstance(result, tuple) and len(result) >= 4:
            has_ambiguity_field = True
        assert has_ambiguity_field, (
            "route() must expose an ambiguity signal (RouteResult.is_ambiguous, or a 4th "
            "tuple element) per Plan.md B2.T1. A vague query must not silently resolve to "
            "one objective with no way for the caller to detect low confidence."
        )

    def test_vague_query_with_no_well_context_flagged_ambiguous(self):
        """B2.T2 — trigger condition: confidence below threshold AND no implicit well resolvable."""
        result = self.router.route("is everything okay?", conversation_context=None)
        is_ambiguous = getattr(result, "is_ambiguous", None)
        if is_ambiguous is None and isinstance(result, tuple) and len(result) >= 4:
            is_ambiguous = result[3]
        if is_ambiguous is None:
            pytest.skip("Ambiguity signal not implemented yet (Phase B2.T1).")
        assert is_ambiguous is True, (
            "'is everything okay?' with no asset context and no conversation history "
            "must be flagged ambiguous per Plan.md B2.T2 trigger condition."
        )

    def test_no_longer_silently_defaults_to_op03(self):
        """
        Regression guard for the exact bug called out in the plan: a vague query used to
        silently land on OP03_FAULT_DIAGNOSIS. Once ambiguity scoring exists, a vague query
        with zero context should either be flagged ambiguous OR route with real justification
        — not silently default with high confidence.
        """
        result = self.router.route("is everything okay?")
        obj_id = getattr(result, "objective_id", None) or (result[0] if isinstance(result, tuple) else None)
        conf = getattr(result, "confidence", None) or (result[1] if isinstance(result, tuple) else None)
        is_ambiguous = getattr(result, "is_ambiguous", None) or (
            result[3] if isinstance(result, tuple) and len(result) >= 4 else None
        )
        if is_ambiguous is None:
            pytest.skip("Ambiguity signal not implemented yet (Phase B2.T1) — cannot check this regression yet.")
        if obj_id == "OP03_FAULT_DIAGNOSIS" and conf and conf > 0.7:
            assert is_ambiguous is True, (
                "Query defaulted to OP03_FAULT_DIAGNOSIS with high confidence but was NOT "
                "flagged ambiguous — this is the exact silent-default bug Plan.md B2 exists to fix."
            )


# ---------------------------------------------------------------------------
# Phase B3 — Clarification node (LangGraph interrupt / HITL)
# ---------------------------------------------------------------------------

class TestPhaseB3_ClarificationNode:
    """Plan.md B3.T1/B3.T2/B3.T3"""

    def test_clarification_node_exists_in_graph(self):
        from src.agent.supervisor import graph as graph_mod
        if not hasattr(graph_mod, "clarification_node"):
            pytest.skip("clarification_node not implemented yet (Phase B3.T1).")
        assert callable(graph_mod.clarification_node)

    def test_clarification_triggers_before_expensive_path(self):
        """
        B3.T1 — for an ambiguous query with no implicit well, the graph must ask a
        clarifying question BEFORE running the full evidence/LLM path (~30-70s).
        Verified by elapsed time being small (<5s) rather than a full advisory run.
        """
        from src.agent.supervisor import graph as graph_mod
        if not hasattr(graph_mod, "clarification_node"):
            pytest.skip("clarification_node not implemented yet (Phase B3.T1).")

        import time
        from src.agent.supervisor.user_entry import UserEntryAdapter
        adapter = UserEntryAdapter()
        sig = inspect.signature(adapter.run)
        if "session_id" not in sig.parameters:
            pytest.skip("Depends on Phase A3 (session_id plumbing) for a truly context-free ambiguous call.")

        session_id = f"TEST-B3-{uuid.uuid4().hex[:8]}"
        t0 = time.time()
        result = adapter.run(
            user_query="morning, can you take a look at things?",
            asset_id=None,
            session_id=session_id,
            request_id="LEVELB-B3-TEST",
        )
        dt = time.time() - t0
        assert dt < 10, (
            f"Ambiguous query with no well context took {dt:.1f}s — expected the clarification "
            f"node to short-circuit BEFORE the ~30-70s evidence/LLM path (Plan.md B3.T1)."
        )
        result_text = str(getattr(result, "assessment", result))
        assert "which well" in result_text.lower() or "clarif" in result_text.lower(), (
            "Expected a clarifying question referencing available wells, not a full advisory."
        )

    def test_resume_contract_continues_same_thread(self):
        """B3.T2 — operator's answer must resume the same thread_id without replaying the whole graph."""
        pytest.skip(
            "Requires a concrete paused-run fixture from B1+B3 together; implement once "
            "the interrupt() payload shape and resume API are defined in Phase B3."
        )


# ---------------------------------------------------------------------------
# Phase B4 — LLM-assisted routing fallback (full 14-objective coverage)
# ---------------------------------------------------------------------------

class TestPhaseB4_LLMRoutingFallback:
    """Plan.md B4.T1/B4.T2/B4.T3"""

    def setup_method(self):
        from src.agent.intent_router import IntentRouter
        self.router = IntentRouter()

    def test_non_technical_phrasing_still_routes_correctly(self):
        """
        B4.T1 — free-form operator language that keyword/semantic paths miss must still
        land on a real objective via the LLM fallback, not misroute.
        SLOW: this test calls the office LLM server if the fallback triggers.
        """
        result = self.router.route("morning, can you take a look at things over at FSWS-001-A?")
        obj_id = getattr(result, "objective_id", None) or (result[0] if isinstance(result, tuple) else result)
        path = getattr(result, "path_used", None) or (
            result[2] if isinstance(result, tuple) and len(result) >= 3 else None
        )
        if path is None or "LLM" not in str(path).upper():
            pytest.skip(
                "LLM-assisted fallback path not implemented yet (Phase B4.T1) — "
                f"current routing landed on {obj_id} via {path} without an LLM hop."
            )
        assert obj_id in (
            "OP01_CURRENT_STATUS", "OP03_FAULT_DIAGNOSIS",
        ), f"Expected a status/diagnosis-family objective for this phrasing, got {obj_id}"

    def test_greeting_generalized_beyond_hardcoded_strings(self):
        """
        B4.T2 — regression guard for the exact gap called out in the plan: greeting
        detection must not be limited to hardcoded exact strings like 'hi'/'hello'.
        """
        obj_id_result = self.router.route("morning, can you take a look at things?")
        obj_id = getattr(obj_id_result, "objective_id", None) or (
            obj_id_result[0] if isinstance(obj_id_result, tuple) else obj_id_result
        )
        # This phrasing is NOT a greeting — it's a real (vague) request. The regression
        # this guards against is the OPPOSITE gap: hardcoded greeting list causing a
        # real non-technical request to be misrouted as OP07_GENERAL_INQUIRY small-talk.
        assert obj_id != "OP07_GENERAL_INQUIRY", (
            "'morning, can you take a look at things?' is a real operational request, not "
            "small talk. If it lands on OP07_GENERAL_INQUIRY, the greeting bucket is still "
            "too broad/hardcoded (Plan.md B4.T2 gap)."
        )

    def test_high_confidence_path_skips_llm_hop(self):
        """B4.T3 — a clear technical phrasing must route in one shot with no extra LLM call (latency guard)."""
        import time
        t0 = time.time()
        self.router.route("Why is FS-031 producing less?")
        dt = time.time() - t0
        assert dt < 2.0, (
            f"Clear technical phrasing took {dt:.2f}s to route — expected sub-2s keyword/semantic "
            f"match with NO LLM hop (Plan.md B4.T3 short-circuit)."
        )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
