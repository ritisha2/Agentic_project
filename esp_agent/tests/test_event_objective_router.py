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

    res = router.route(user_query="", event_code="ESP_TRIPPED")
    assert res.objective_id == "OP03_FAULT_DIAGNOSIS"
    assert res.confidence == 1.0
    assert res.path == "Path_C_Event"
    assert not res.is_ambiguous

    res2 = router.route(user_query="", event_code="PRODUCTION_DECLINE_DETECTED")
    assert res2.objective_id == "OP02_PRODUCTION_DECLINE_RCA"
    assert res2.confidence == 1.0
    assert res2.path == "Path_C_Event"
    assert not res2.is_ambiguous


def test_intent_router_greeting_option_c():
    """Verify Option C collapses elongated greetings algorithmically and maps to OP07."""
    router = IntentRouter()
    for greeting in ["hi", "hiiiii", "heyyy", "heeeello", "good morning", "hi there!"]:
        res = router.route(user_query=greeting)
        assert res.objective_id == "OP07_GENERAL_INQUIRY"
        assert res.path == "Path_A_Greeting"
        assert not res.is_ambiguous
