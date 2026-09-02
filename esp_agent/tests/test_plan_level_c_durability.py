"""
Level C Verification Suite — Durability & Long-Term Memory
Grounded in Plan.md §LEVEL C (Phases C1–C2)

Run with:
    .venv\\Scripts\\python.exe -m pytest tests/test_plan_level_c_durability.py -v
"""

import uuid
import time
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest

from src.schemas.advisory import StandardAdvisoryPayload
from src.memory.well_memory import WellEpisodicMemoryStore
from src.memory.redis_checkpointer import RedisCheckpointer
from src.llm.context_builder import CompactContextBuilder


# ---------------------------------------------------------------------------
# Phase C1 — Episodic / Long-Term Memory Tier
# ---------------------------------------------------------------------------

class TestPhaseC1_WellEpisodicMemory:
    """Plan.md C1.T1/C1.T2 — per-well episodic store and prompt retrieval."""

    def setup_method(self):
        self.store = WellEpisodicMemoryStore()
        self.test_well = f"TEST-WELL-{uuid.uuid4().hex[:6].upper()}"

    def teardown_method(self):
        self.store.clear(self.test_well)

    def _make_advisory(self, asset_id: str, diagnosis: str, recommendation: str, obj: str = "OP01_CURRENT_STATUS"):
        return StandardAdvisoryPayload(
            advisory_id=f"ADV-{uuid.uuid4().hex[:8]}",
            asset_id=asset_id,
            objective_id=obj,
            timestamp=datetime.utcnow().isoformat(),
            assessment=f"Assessment for {asset_id}: {diagnosis}",
            diagnosis=diagnosis,
            confidence=0.92,
            risk="Medium",
            recommendation=recommendation,
            expected_impact="High reliability",
            provenance=["Level C Test"],
        )

    def test_record_and_get_well_memory(self):
        """C1.T1 — record advisory updates the well memory and retrieves the latest summary."""
        advisory = self._make_advisory(
            asset_id=self.test_well,
            diagnosis="High Motor Temperature (128°C)",
            recommendation="Reduce operating frequency to 45Hz",
        )
        self.store.record_advisory(self.test_well, advisory)

        mem = self.store.get_memory(self.test_well)
        assert mem is not None, "Expected memory record for well after recording advisory."
        assert mem["well_id"] == self.test_well
        assert mem["total_assessments"] == 1
        assert "High Motor Temperature" in mem["last_diagnosis"]
        assert "Reduce operating frequency" in mem["last_recommendation"]
        assert len(mem["recent_events"]) == 1

    def test_cross_session_durability(self):
        """
        C1.T1 — verify that episodic memory survives across completely different sessions.
        Session 1 diagnoses the well; Session 2 opens and immediately sees prior findings.
        """
        session_1 = f"SESS-{uuid.uuid4().hex[:8]}"
        session_2 = f"SESS-{uuid.uuid4().hex[:8]}"

        advisory = self._make_advisory(
            asset_id=self.test_well,
            diagnosis="Intake Gas Interference",
            recommendation="Adjust choke to stabilize PIP",
        )
        self.store.record_advisory(self.test_well, advisory)

        # Fresh store instance simulates a new request/session cycle
        fresh_store = WellEpisodicMemoryStore()
        prompt_ctx = fresh_store.format_prompt_context(self.test_well)

        assert prompt_ctx is not None
        assert prompt_ctx["prior_diagnosis"] == "Intake Gas Interference"
        assert "Adjust choke" in prompt_ctx["prior_recommendation"]

    def test_sliding_window_events(self):
        """C1.T1 — events list is capped at max 5 rolling entries to prevent unbounded growth."""
        for i in range(8):
            advisory = self._make_advisory(
                asset_id=self.test_well,
                diagnosis=f"Diagnosis iteration {i}",
                recommendation=f"Recommendation iteration {i}",
            )
            self.store.record_advisory(self.test_well, advisory)

        mem = self.store.get_memory(self.test_well)
        assert mem["total_assessments"] == 8
        assert len(mem["recent_events"]) == 5
        assert mem["recent_events"][-1]["diagnosis"] == "Diagnosis iteration 7"

    def test_redis_down_fallback(self):
        """C1.T1 — when Redis is unavailable, in-memory fallback stores and retrieves gracefully."""
        with patch.object(self.store.connection_mgr, "get_client", side_effect=Exception("Redis down")):
            advisory = self._make_advisory(
                asset_id=self.test_well,
                diagnosis="Mechanical Pump Wear",
                recommendation="Schedule workover",
            )
            self.store.record_advisory(self.test_well, advisory)
            mem = self.store.get_memory(self.test_well)
            assert mem is not None
            assert mem["last_diagnosis"] == "Mechanical Pump Wear"

    def test_context_builder_injects_episodic_memory(self):
        """C1.T2 — CompactContextBuilder injects episodic_well_memory into compact context dict."""
        builder = CompactContextBuilder()
        state = {
            "request": {"asset_id": self.test_well},
            "run": {"objective_id": "OP01_CURRENT_STATUS"},
            "context": {
                "episodic_memory": {
                    "last_updated": "2026-09-02T12:00:00Z",
                    "last_objective": "OP03_FAULT_DIAGNOSIS",
                    "last_diagnosis": "High Vibration 4.2 mm/s",
                    "last_recommendation": "Inspect drive bearings",
                }
            },
            "specialist_results": [],
            "evidence_refs": [],
            "safety_state": {},
            "conflicts": [],
        }
        compact = builder.build_from_agent_state(state)
        assert "episodic_well_memory" in compact, "compact context must include episodic_well_memory"
        assert compact["episodic_well_memory"]["prior_diagnosis"] == "High Vibration 4.2 mm/s"
        assert compact["episodic_well_memory"]["prior_recommendation"] == "Inspect drive bearings"


# ---------------------------------------------------------------------------
# Phase C2 — Restart-Safe Graph Execution
# ---------------------------------------------------------------------------

class TestPhaseC2_RestartSafeCheckpointer:
    """Plan.md C2.T1 — RedisCheckpointer ensures thread checkpoints survive process bounces."""

    def setup_method(self):
        self.thread_id = f"THREAD-TEST-{uuid.uuid4().hex[:8]}"

    def teardown_method(self):
        saver = RedisCheckpointer()
        saver.delete_thread(self.thread_id)

    def test_redis_checkpointer_saves_and_loads_across_instances(self):
        """C2.T1 — instance 1 puts a checkpoint, fresh instance 2 hydrates it via get_tuple()."""
        saver_1 = RedisCheckpointer()
        cfg = {"configurable": {"thread_id": self.thread_id, "checkpoint_ns": ""}}

        checkpoint = {
            "id": f"chk-{uuid.uuid4().hex[:6]}",
            "v": 1,
            "ts": datetime.utcnow().isoformat(),
            "channel_values": {"asset_id": "FSWS-001-A", "step": "clarification"},
            "channel_versions": {"asset_id": "1", "step": "1"},
            "versions_seen": {},
        }
        saved_cfg = saver_1.put(cfg, checkpoint, {}, {"asset_id": "1", "step": "1"})
        assert saved_cfg["configurable"]["checkpoint_id"] == checkpoint["id"]

        # Simulate fresh process: create new RedisCheckpointer instance with EMPTY in-memory storage
        saver_2 = RedisCheckpointer()
        assert self.thread_id not in saver_2.storage

        tuple_loaded = saver_2.get_tuple(cfg)
        assert tuple_loaded is not None, "Checkpoint must be hydrated from Redis in fresh instance."
        assert tuple_loaded.checkpoint["id"] == checkpoint["id"]
        assert tuple_loaded.checkpoint["channel_values"]["asset_id"] == "FSWS-001-A"
        assert tuple_loaded.checkpoint["channel_values"]["step"] == "clarification"

    def test_supervisor_graph_uses_redis_checkpointer(self):
        """C2.T1 — supervisor_graph must be compiled with RedisCheckpointer."""
        from src.agent.supervisor import graph as graph_mod
        checkpointer = getattr(graph_mod.supervisor_graph, "checkpointer", None)
        assert checkpointer is not None
        assert isinstance(checkpointer, RedisCheckpointer), (
            f"Expected RedisCheckpointer on supervisor_graph, got {type(checkpointer)}"
        )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
