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

logger = logging.getLogger(__name__)


class UserEntryAdapter:
    """
    Adapter processing HTTP REST / MCP user queries through the Phase 7 LangGraph Supervisor.
    """

    def __init__(self, intent_router: Optional[IntentRouter] = None):
        self.intent_router = intent_router or IntentRouter()

    def run(
        self,
        user_query: str,
        asset_id: str,
        request_id: str = "REQ-001",
        tenant_id: Optional[str] = None
    ) -> StandardAdvisoryPayload:
        """
        Classify intent, initialize AgentState, and execute Supervisor Graph.
        """
        obj_id, conf, path = self.intent_router.route(user_query)
        logger.info(f"UserEntryAdapter: Query '{user_query[:30]}' -> objective '{obj_id}' via {path} (conf={conf:.2f})")

        initial_state = create_initial_agent_state(
            run_id=request_id,
            asset_id=asset_id,
            user_query=user_query,
            objective_id=obj_id,
            trigger_type="user"
        )

        final_state = supervisor_graph.invoke(initial_state)
        advisory_dict = final_state.get("advisory_draft")

        if advisory_dict:
            advisory = StandardAdvisoryPayload(**advisory_dict)
            advisory.provenance.append(f"User Entry Adapter v7.0 ({path})")
            return advisory

        raise RuntimeError(f"Supervisor Graph execution failed to produce advisory for request '{request_id}'.")
