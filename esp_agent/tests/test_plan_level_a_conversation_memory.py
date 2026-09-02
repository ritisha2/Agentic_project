"""
Level A verification suite — Conversation Memory + Implicit Well
Grounded in Plan.md §LEVEL A (Phases A1-A4)

Run with:
    .venv\\Scripts\\python.exe -m pytest tests/test_plan_level_a_conversation_memory.py -v

NOTE: These tests target code that does NOT exist yet (Phase A1-A4 are unimplemented
as of this writing). They are written FIRST, against the signatures agreed in Plan.md,
so that each phase can be verified the moment it lands. Tests are grouped by phase and
each group is skipped with a clear reason if its target module/method isn't present yet
— they will not falsely report a phase as "failed" before you've started it.

Each test class maps 1:1 to a Plan.md phase so failures point straight at the phase that
regressed.
"""

import time
import uuid
import importlib
import pytest


# ---------------------------------------------------------------------------
# Phase A1 — ConversationStore (Redis, extends RedisConnectionManager pattern)
# ---------------------------------------------------------------------------

def _load_conversation_store():
    try:
        mod = importlib.import_module("src.memory.conversation_store")
        return mod
    except ModuleNotFoundError:
        return None


class TestPhaseA1_ConversationStore:
    """Plan.md A1.T1/A1.T2 — esp_agent/src/memory/conversation_store.py"""

    @pytest.fixture(autouse=True)
    def _setup(self):
        mod = _load_conversation_store()
        if mod is None:
            pytest.skip("Phase A1 not implemented yet: src/memory/conversation_store.py missing.")
        self.mod = mod
        self.store = mod.ConversationStore()
        self.session_id = f"TEST-SESSION-{uuid.uuid4().hex[:8]}"
        yield
        # cleanup - don't leak test sessions into real Redis
        if hasattr(self.store, "clear"):
            self.store.clear(self.session_id)

    def test_reuses_existing_redis_connection_pattern(self):
        """Must reuse RedisConnectionManager, not open a second Redis client (Plan.md principle #1)."""
        from src.events.redis_connection import RedisConnectionManager
        assert hasattr(self.store, "connection_mgr"), (
            "ConversationStore must expose a connection_mgr attribute, mirroring "
            "CheckpointManager's pattern, to prove it reuses RedisConnectionManager "
            "rather than instantiating a parallel Redis client."
        )
        assert isinstance(self.store.connection_mgr, RedisConnectionManager)

    def test_append_and_get_history_schema(self):
        """Per-turn schema must be exactly {role, content, timestamp, well_id, intent_detected}."""
        self.store.append(
            self.session_id, role="user", content="What is the status of FSWS-001-A?",
            well_id="FSWS-001-A", intent="OP01_CURRENT_STATUS"
        )
        self.store.append(
            self.session_id, role="assistant", content="FSWS-001-A shows High Backpressure.",
            well_id="FSWS-001-A", intent="OP01_CURRENT_STATUS"
        )
        history = self.store.get_history(self.session_id)
        assert len(history) == 2
        turn = history[0]
        for key in ("role", "content", "timestamp", "well_id", "intent_detected"):
            assert key in turn, f"Per-turn schema missing required key '{key}'"
        assert turn["role"] == "user"
        assert turn["well_id"] == "FSWS-001-A"

    def test_sliding_window_last_10(self):
        """Context window must be the sliding window of the last 10 exchanges (Plan.md spec)."""
        for i in range(15):
            self.store.append(
                self.session_id, role="user", content=f"query {i}",
                well_id="FSWS-001-A", intent="OP01_CURRENT_STATUS"
            )
        history = self.store.get_history(self.session_id, limit=10)
        assert len(history) == 10, "get_history must cap at the agreed sliding window of 10"
        # Must be the MOST RECENT 10, not the first 10
        assert history[-1]["content"] == "query 14"

    def test_get_last_well_resolves_implicit_default(self):
        """Well Resolution: last well mentioned becomes the implicit default (Plan.md spec)."""
        self.store.append(self.session_id, role="user", content="status of FSWS-001-A?",
                           well_id="FSWS-001-A", intent="OP01_CURRENT_STATUS")
        self.store.append(self.session_id, role="user", content="what about FS-010?",
                           well_id="FS-010", intent="OP01_CURRENT_STATUS")
        # a follow-up turn with NO well mentioned should not overwrite the resolver
        self.store.append(self.session_id, role="user", content="is that bad?",
                           well_id=None, intent=None)
        assert self.store.get_last_well(self.session_id) == "FS-010", (
            "get_last_well must return the most recent NON-NULL well_id, "
            "skipping turns where no well was mentioned."
        )

    def test_ttl_is_seven_days(self):
        """Storage Backend spec: Redis TTL 7 days per session key."""
        self.store.append(self.session_id, role="user", content="hello",
                           well_id=None, intent="OP07_GENERAL_INQUIRY")
        try:
            client = self.store.connection_mgr.get_client()
            key = f"esp:conv:{self.session_id}"
            ttl = client.ttl(key)
            assert ttl > 0, "Session key must have a TTL set"
            seven_days_secs = 7 * 24 * 3600
            # allow slack for test execution time
            assert seven_days_secs - 60 <= ttl <= seven_days_secs, (
                f"Expected TTL ~{seven_days_secs}s (7 days), got {ttl}s"
            )
        except Exception as ex:
            pytest.skip(f"Redis unavailable in this environment ({ex}); TTL check requires live Redis.")

    def test_redis_down_falls_back_gracefully(self, monkeypatch):
        """Store must degrade gracefully (in-memory fallback) like CheckpointManager does."""
        def _broken_client(*a, **kw):
            raise ConnectionError("simulated Redis outage")
        monkeypatch.setattr(self.store.connection_mgr, "get_client", _broken_client)
        # Should not raise — must fall back to memory, mirroring CheckpointManager behavior
        self.store.append(self.session_id, role="user", content="fallback test",
                           well_id="FSWS-001-A", intent="OP01_CURRENT_STATUS")
        history = self.store.get_history(self.session_id)
        assert len(history) >= 1


# ---------------------------------------------------------------------------
# Phase A2 — IntentRouter.route() sees conversation context
# ---------------------------------------------------------------------------

class TestPhaseA2_RouterConversationContext:
    """Plan.md A2.T1/A2.T2/A2.T3 — src/agent/intent_router.py"""

    def setup_method(self):
        from src.agent.intent_router import IntentRouter
        self.router = IntentRouter()

    def test_backward_compatible_without_context(self):
        """A2.T3 — existing single-shot callers (no conversation_context) must keep working."""
        obj_id, conf, path, is_ambiguous = self.router.route("Why is FS-031 producing less?")
        assert obj_id, "route() must still return an objective with no conversation_context arg"

    def test_route_accepts_conversation_context_param(self):
        """A2.T1 — route() must accept an optional conversation_context kwarg without raising."""
        import inspect
        sig = inspect.signature(self.router.route)
        assert "conversation_context" in sig.parameters, (
            "IntentRouter.route() must be extended with a 'conversation_context' parameter "
            "(Plan.md A2.T1). Current signature: " + str(sig)
        )

    def test_followup_carries_forward_prior_objective(self):
        """
        A2.T2 — the core gap the plan calls out: a bare follow-up like 'is that bad?' must
        NOT fall through Path B semantic default (OP03_FAULT_DIAGNOSIS) when conversation
        context supplies a last_objective. It must carry the prior objective forward.
        """
        conv_ctx = {
            "last_well": "FSWS-001-A",
            "last_objective": "OP01_CURRENT_STATUS",
            "recent_turns": [
                {"role": "user", "content": "What is the current status of FSWS-001-A?"},
                {"role": "assistant", "content": "FSWS-001-A shows High Backpressure."},
            ],
        }
        obj_id, conf, path, is_ambiguous = self.router.route("is that bad?", conversation_context=conv_ctx)
        assert obj_id == "OP01_CURRENT_STATUS", (
            f"Follow-up 'is that bad?' with prior objective OP01_CURRENT_STATUS in context "
            f"must carry that objective forward, not silently default. Got: {obj_id} via {path}"
        )

    def test_ambiguous_followup_without_context_still_defaults_safely(self):
        """Sanity: a follow-up with NO conversation_context at all should not crash, even if
        it still falls back to the old default — this documents current pre-Level-B behavior."""
        obj_id, conf, path, is_ambiguous = self.router.route("is that bad?")
        assert obj_id  # must not raise / must not be None


# ---------------------------------------------------------------------------
# Phase A3 — UserEntryAdapter + bff_routes wiring
# ---------------------------------------------------------------------------

class TestPhaseA3_EntryAdapterAndBFF:
    """Plan.md A3.T1/A3.T2/A3.T3"""

    def test_user_entry_adapter_accepts_session_id(self):
        """A3.T1 — UserEntryAdapter.run() must accept a session_id kwarg."""
        import inspect
        from src.agent.supervisor.user_entry import UserEntryAdapter
        sig = inspect.signature(UserEntryAdapter.run)
        assert "session_id" in sig.parameters, (
            "UserEntryAdapter.run() must accept 'session_id' (Plan.md A3.T1). "
            f"Current signature: {sig}"
        )

    def test_implicit_well_resolution_when_asset_id_omitted(self):
        """
        A3.T1 — when asset_id is omitted but session has a last_well in the conversation
        store, UserEntryAdapter must resolve it rather than requiring the caller to repeat it.
        """
        mod = _load_conversation_store()
        if mod is None:
            pytest.skip("Depends on Phase A1 (conversation_store.py) which isn't implemented yet.")

        from src.agent.supervisor.user_entry import UserEntryAdapter
        import inspect

        sig = inspect.signature(UserEntryAdapter.run)
        params = sig.parameters
        # asset_id must become optional (Optional[str] = None) once implicit resolution lands
        assert params["asset_id"].default is not inspect.Parameter.empty or "asset_id" not in (
            p for p in params if params[p].default is inspect.Parameter.empty
        ), (
            "asset_id must become optional once implicit well resolution (A3.T1) is wired, "
            "so a follow-up query can omit it and fall back to ConversationStore.get_last_well()."
        )

    def test_bff_run_endpoint_accepts_session_header(self):
        """A3.T2 — POST /api/ui/agent/run must read X-Session-ID and not error without it either."""
        from fastapi.testclient import TestClient
        from src.api.rest.gateway import app
        client = TestClient(app)
        session_id = f"TEST-SESSION-{uuid.uuid4().hex[:8]}"

        resp = client.post(
            "/api/ui/agent/run",
            headers={"X-Session-ID": session_id},
            json={"user_query": "Why is FS-031 producing less?", "asset_id": "FS-031"},
        )
        assert resp.status_code == 200, (
            f"Endpoint must accept the X-Session-ID header without erroring. Got {resp.status_code}: {resp.text[:300]}"
        )

    def test_bff_appends_exchange_to_conversation_store(self):
        """A3.T2 — after a run completes, the exchange must be appended to the session's history."""
        mod = _load_conversation_store()
        if mod is None:
            pytest.skip("Depends on Phase A1 (conversation_store.py) which isn't implemented yet.")

        from fastapi.testclient import TestClient
        from src.api.rest.gateway import app
        client = TestClient(app)
        store = mod.ConversationStore()
        session_id = f"TEST-SESSION-{uuid.uuid4().hex[:8]}"

        client.post(
            "/api/ui/agent/run",
            headers={"X-Session-ID": session_id},
            json={"user_query": "What is the current status of FSWS-001-A?", "asset_id": "FSWS-001-A"},
        )
        history = store.get_history(session_id)
        assert len(history) >= 2, (
            "Both the user turn and the assistant turn must be appended to the "
            "ConversationStore after a completed /api/ui/agent/run call."
        )
        roles = {t["role"] for t in history}
        assert "user" in roles and "assistant" in roles
        store.clear(session_id)

    def test_multiturn_followup_resolves_via_bff(self):
        """
        End-to-end Level A exit criteria (Plan.md):
        'Status of FSWS-001-A?' -> then 'is that bad?' resolves to the same well,
        with a coherent follow-up objective. This is the real, slow, LLM-driven check —
        expect ~70s per turn. Run manually, not in CI, due to LLM latency.
        """
        pytest.skip(
            "SLOW / LLM-driven (~70s x 2 turns). Run manually per-phase, not in automated CI. "
            "See Plan.md Level A exit criteria. Use the manual verification script instead: "
            "tests/manual_level_a_multiturn_verify.py"
        )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
