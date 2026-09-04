"""
Test Suite: KB Vertical Slice & Cognee Patterns Verification
Validates:
- Gaps 1, 2, 3, 4, 6 fixed
- Cognee Patterns 1, 2, 3, 4 active
- Grounded evidence tokens & deep links populated in OP06 responses
"""

import pytest
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
ESP_AGENT_DIR = ROOT_DIR / "esp_agent"
if str(ESP_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(ESP_AGENT_DIR))


def test_gap6_and_gap3_knowledge_specialist():
    """Verify specialist uses vector_results and does NOT return fake SOP-014."""
    from src.agent.specialists.knowledge import knowledge_graph

    # Query something distinct
    res = knowledge_graph.invoke({
        "input": {"task": "What is the procedure for backspin?"},
        "citations": [],
        "findings": [],
        "evidence_refs": [],
        "output": None
    })
    output = res.get("output")
    assert output is not None
    assert output["status"] == "complete"
    # Verify no fake SOP-014 fabricated if not relevant
    refs = output.get("evidence_refs", [])
    for r in refs:
        assert "SOP-014:p3" not in r or "backspin" in r.lower()


def test_cognee_pattern1_graph_to_chunk_linking():
    """Verify GraphAdapter resolves nodes to grounded vector chunk IDs."""
    from src.adapters.graph import GraphAdapter
    graph = GraphAdapter()
    
    # Motor Overheating node should have mapped chunk_ids
    chunks = graph.get_node_chunk_ids("Motor Overheating")
    assert len(chunks) > 0
    assert "DOC-STD-API-11S_p14_c1" in chunks

    # Traces should attach chunk_ids
    traces = graph.trace_cause_effect("Motor Overheating")
    if traces:
        assert "chunk_ids" in traces[0]


def test_cognee_pattern2_subgraph_constrained_retrieval():
    """Verify hybrid_retrieve accepts document_filter and chunk_id_filter."""
    from src.services.retrieval_service import RetrievalService
    svc = RetrievalService()
    
    res = svc.hybrid_retrieve(
        query="Motor temperature trip limits",
        top_k=2,
        chunk_id_filter=["DOC-STD-API-11S_p14_c1"]
    )
    assert "vector_results" in res
    assert "retrieval_status" in res


def test_cognee_pattern3_pydantic_ontology():
    """Verify strict Pydantic ontology model validates properly."""
    from src.schemas.ontology import FailureChain, ESPMetricEnum, FaultTaxonomyEnum, SubsystemEnum

    chain = FailureChain(
        symptom="High Motor Temperature",
        primary_metric=ESPMetricEnum.MOTOR_TEMP,
        mechanism="Stator insulation failure from deadheading",
        failure_mode=FaultTaxonomyEnum.MOTOR_OVERHEATING,
        affected_subsystem=SubsystemEnum.MOTOR,
        affected_component="Stator Winding",
        recommended_action="Controlled shutdown, verify cooling flow",
        source_document_id="DOC-STD-API-11S",
        page=14,
        chunk_ids=["DOC-STD-API-11S_p14_c1"]
    )
    assert chain.failure_mode == "Motor Overheating"
    assert chain.primary_metric == "motor_temperature"


def test_cognee_pattern4_unified_memory_gateway():
    """Verify MemoryGateway integrates Graph, Vector, and Telemetry in one call."""
    from src.services.memory_gateway import memory_gateway

    mem = memory_gateway.recall(asset_id="FS-031", query="motor overheating and thermal limits", top_k=2)
    assert mem["asset_id"] == "FS-031"
    assert "causal_traces" in mem
    assert "linked_chunk_ids" in mem
    assert "vector_results" in mem


def test_gap1_and_gap4_op06_advisory_citations():
    """Verify OP06 generates populated evidence list with deep links."""
    from src.agent.supervisor.user_entry import UserEntryAdapter

    adapter = UserEntryAdapter()
    adv = adapter.run(
        user_query="What is the standard operating procedure for pump startup?",
        asset_id="FS-031",
        request_id="REQ-TEST-KB-001",
        session_id="SESS-TEST-KB"
    )
    
    assert adv.objective_id == "OP06_PROCEDURE_LOOKUP"
    assert "Startup" in adv.assessment or "Procedure" in adv.assessment or "API RP 11S" in adv.assessment
    
    # Gap 1 verification: evidence MUST NOT be empty
    assert len(adv.evidence) > 0
    first_ev = adv.evidence[0]
    ev_dict = first_ev if isinstance(first_ev, dict) else first_ev.model_dump()
    assert ev_dict["source_type"] == "Knowledge Base"
    assert "API_RP_11S" in ev_dict["source_id"] or "esp:kb:" in ev_dict["source_id"]
    assert ev_dict["source_deep_link"] is not None
