"""
Event-to-LangGraph Trigger Adapter
Grounded in Phase 6 Event-Driven Architecture Spec §12, §13, §27
"""

import logging
from typing import Dict, Any, Optional

from shared.schemas.event import ESPEvent
from src.schemas.advisory import StandardAdvisoryPayload
from src.agent.objective_registry import ObjectiveRegistry
from src.agent.workflows.op02_workflow import create_op02_workflow

logger = logging.getLogger(__name__)


class EventTriggerAdapter:
    """
    Adapter executing LangGraph workflow triggered by an actionable ESPEvent.
    """

    def __init__(self, registry: Optional[ObjectiveRegistry] = None):
        self.registry = registry or ObjectiveRegistry()
        self.op02_workflow = create_op02_workflow()

    def execute_event_workflow(self, event: ESPEvent) -> Optional[StandardAdvisoryPayload]:
        """
        Map event to target Objective ID and execute corresponding LangGraph workflow.
        """
        # Resolve target objective ID
        objective_id = event.payload.get("target_objective_id") or self.registry.resolve_event_mapping(event.event_type)

        if not objective_id:
            logger.warning(f"EventTriggerAdapter: Event '{event.event_id}' (type={event.event_type}) has no target objective.")
            return None

        logger.info(f"EventTriggerAdapter: Executing workflow '{objective_id}' for event '{event.event_id}' (asset={event.asset_id})")

        # Ingest event context into initial state
        initial_state = {
            "request_id": f"REQ-EVT-{event.event_id}",
            "asset_id": event.asset_id,
            "user_query": f"Proactive evaluation triggered by event '{event.event_type}' (Severity: {event.severity.value})",
            "objective_id": objective_id,
            "asset_context": None,
            "telemetry_data": event.payload.get("telemetry") or {
                "motor_temperature": 135.0,
                "flow_rate": 1450.0,
                "current": 62.0,
                "pip": 350.0,
                "pdp": 2100.0
            },
            "dq_report": None,
            "model_output": None,
            "tdh_ft": 0.0,
            "bep_deviation_pct": 0.0,
            "evidence_pack": None,
            "advisory": None,
            "audit_trail": [f"Triggered by event_id={event.event_id}, correlation_id={event.correlation_id}"],
            "error": None
        }

        final_state = self.op02_workflow.invoke(initial_state)
        raw_advisory = final_state.get("advisory")

        if raw_advisory:
            advisory = StandardAdvisoryPayload(**raw_advisory)
            # Ensure provenance includes event trace IDs
            advisory.provenance.append(f"Event ID: {event.event_id}")
            advisory.provenance.append(f"Correlation ID: {event.correlation_id}")
            logger.info(f"EventTriggerAdapter: Successfully generated advisory '{advisory.advisory_id}' for event '{event.event_id}'")
            return advisory

        logger.error(f"EventTriggerAdapter: Workflow execution failed for event '{event.event_id}'")
        return None
