"""
Unit tests for ObjectiveRegistry event mapping resolution and IntentRouter Path C refactor
Grounded in Phase 6 Event-Driven Architecture Spec §11, §26
"""

import pytest
from src.agent.objective_registry import ObjectiveRegistry
from src.agent.intent_router import IntentRouter


def test_objective_registry_event_mapping():
    """Verify ObjectiveRegistry acts as single authority for event mapping resolution."""
    registry = ObjectiveRegistry()
    assert registry.resolve_event_mapping("ESP_TRIPPED") == "OP03_FAULT_DIAGNOSIS"
    assert registry.resolve_event_mapping("FAILURE_RISK_INCREASED") == "OP05_EARLY_WARNING"
    assert registry.resolve_event_mapping("PRODUCTION_DECLINE_DETECTED") == "OP02_PRODUCTION_DECLINE_RCA"
    assert registry.resolve_event_mapping("UNKNOWN_EVENT") is None


def test_intent_router_delegates_to_objective_registry():
    """Verify IntentRouter Path C delegates to ObjectiveRegistry without hardcoded EVENT_CODE_MAP."""
    registry = ObjectiveRegistry()
    router = IntentRouter(registry=registry)

    obj_id, conf, path = router.route(user_query="", event_code="ESP_TRIPPED")
    assert obj_id == "OP03_FAULT_DIAGNOSIS"
    assert conf == 1.0
    assert path == "Path_C_Event"

    obj_id2, conf2, path2 = router.route(user_query="", event_code="PRODUCTION_DECLINE_DETECTED")
    assert obj_id2 == "OP02_PRODUCTION_DECLINE_RCA"
    assert conf2 == 1.0
    assert path2 == "Path_C_Event"
