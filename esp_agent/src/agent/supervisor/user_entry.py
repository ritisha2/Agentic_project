"""
User Entry Adapter for Phase 7 Supervisor Graph
Grounded in ESP_APM_PHASE_7_LangGraph_Supervisor_MultiAgent_Architecture_Design.docx §8, §24
"""

import logging
from typing import Optional, Dict, Any

from src.schemas.advisory import StandardAdvisoryPayload
from src.agent.intent_router import IntentRouter
from src.agent.supervisor.state import create_initial_agent_state
from src.agent.supervisor.graph import supervisor_graph
from src.memory.conversation_store import ConversationStore

logger = logging.getLogger(__name__)


class UserEntryAdapter:
    """
    Adapter processing HTTP REST / MCP user queries through the Phase 7 LangGraph Supervisor.
    """

    def __init__(
        self,
        intent_router: Optional[IntentRouter] = None,
        conversation_store: Optional[ConversationStore] = None,
    ):
        self.intent_router = intent_router or IntentRouter()
        self.conv_store = conversation_store or ConversationStore()

    def run(
        self,
        user_query: str,
        asset_id: Optional[str] = None,
        request_id: str = "REQ-001",
        tenant_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> StandardAdvisoryPayload:
        """
        Classify intent, initialize AgentState, and execute Supervisor Graph.

        A3.T1 additions:
        - When asset_id is blank/None, resolve from ConversationStore.get_last_well().
        - Build conversation_context and pass it into route().
        - Thread recent_turns into state context.history so the LLM narrative sees them.
        - Persist user and assistant turns to ConversationStore if session_id is active.
        """
        # ── Resolve implicit well from conversation memory (A3.T1) ────────────
        resolved_asset_id = asset_id
        recent_turns: list = []
        last_objective: Optional[str] = None

        if session_id:
            if not resolved_asset_id:
                resolved_asset_id = self.conv_store.get_last_well(session_id) or ""
            recent_turns = self.conv_store.get_history(session_id, limit=10)
            # Most recent assistant turn's intent becomes last_objective
            for turn in reversed(recent_turns):
                if turn.get("role") == "assistant" and turn.get("intent_detected"):
                    last_objective = turn["intent_detected"]
                    break
            # Record user turn
            self.conv_store.append(
                session_id=session_id,
                role="user",
                content=user_query,
                well_id=resolved_asset_id or None,
            )


        conversation_context: Optional[Dict[str, Any]] = None
        if session_id:
            conversation_context = {
                "last_well": resolved_asset_id or None,
                "last_objective": last_objective,
                "recent_turns": recent_turns,
            }

        # ── Route intent (A2 signature — backwards-compat when no ctx) ────────
        obj_id, conf, path = self.intent_router.route(
            user_query,
            conversation_context=conversation_context,
        )
        logger.info(
            "UserEntryAdapter: Query '%s' -> objective '%s' via %s (conf=%.2f) session=%s",
            user_query[:40], obj_id, path, conf, session_id or "none",
        )

        initial_state = create_initial_agent_state(
            run_id=request_id,
            asset_id=resolved_asset_id or "UNKNOWN",
            user_query=user_query,
            objective_id=obj_id,
            trigger_type="user",
        )
        # Thread conversation history into state so the LLM narrative node can see it
        initial_state["context"]["history"] = recent_turns

        final_state = supervisor_graph.invoke(initial_state)
        advisory_dict = final_state.get("advisory_draft")

        if advisory_dict:
            advisory = StandardAdvisoryPayload(**advisory_dict)
            advisory.provenance.append(f"User Entry Adapter v7.0 ({path})")
            if session_id:
                agent_content = getattr(advisory, "assessment", None) or getattr(advisory, "diagnosis", None) or advisory.objective_id
                self.conv_store.append(

                    session_id=session_id,
                    role="assistant",
                    content=str(agent_content)[:500],
                    well_id=resolved_asset_id or None,
                    intent=advisory.objective_id,
                )
            return advisory


        raise RuntimeError(f"Supervisor Graph execution failed to produce advisory for request '{request_id}'.")

