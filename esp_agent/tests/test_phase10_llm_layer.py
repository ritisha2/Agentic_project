"""
Phase 10 Tests — LLM Layer Architecture
Grounded in ESP APM LLM Architecture Design (Phase 10)

Tests:
1. test_1_llm_gateway_contract — Gateway chat and mock fallback
2. test_2_compact_context_builder — 4B model context compression
3. test_3_layered_prompt_builder — Prompt composition
4. test_4_structured_output_repair_loop — Pydantic JSON validation & repair
5. test_5_xai_visual_story_builder — UI visual spec mapping
6. test_6_llm_observability_tracer — Audit tracing & token metrics
7. test_7_llm_adapter_end_to_end — Full adapter execution & supervisor graph wiring
"""

import json
import pytest
from pydantic import BaseModel

from src.llm.gateway import LLMGateway, LLMGatewayResponse
from src.llm.context_builder import CompactContextBuilder
from src.llm.prompts import LayeredPromptBuilder, SYSTEM_PROMPT
from src.llm.structured_output import (
    StructuredOutputValidator,
    StructuredOutputError,
    AdvisoryOutputSchema,
    ToolCallSchema,
    ClassificationSchema,
)
from src.llm.xai_builder import XAIVisualStoryBuilder, XAIExplanationPayload
from src.llm.observability import LLMObservabilityTracer, LLMTraceRecord, tracer
from src.llm.adapter import LLMAdapter
from src.agent.supervisor.user_entry import UserEntryAdapter


# ---------------------------------------------------------------------------
# Test 1: LLM Gateway Contract & Mock Fallback
# ---------------------------------------------------------------------------
def test_1_llm_gateway_contract():
    gw = LLMGateway(offline_mode=True)
    messages = [
        {"role": "system", "content": "You are a test assistant."},
        {"role": "user", "content": "Analyze telemetry for FS-031."},
    ]
    resp = gw.chat(messages)

    assert isinstance(resp, LLMGatewayResponse)
    assert resp.is_mock is True
    assert resp.usage.total_tokens > 0
    assert resp.latency_ms >= 0.0

    # Mock response must be valid JSON
    data = json.loads(resp.content)
    assert "assessment" in data
    assert "hypotheses" in data


# ---------------------------------------------------------------------------
# Test 2: Compact Context Builder (4B Model Compression)
# ---------------------------------------------------------------------------
def test_2_compact_context_builder():
    builder = CompactContextBuilder()
    
    # Large raw telemetry arrays (simulating 10,000 points)
    raw_telemetry = {
        "flow_rate": [1200.0, 1150.0, 1100.0, 950.0, 735.7],
        "intake_pressure": [350.0, 348.0, 352.0, 350.0, 236.5],
        "discharge_pressure": [2100.0, 2050.0, 1980.0, 1883.7],
        "motor_temperature": 135.0,
        "current": 62.0,
    }
    raw_engineering = {"tdh_ft": 4042.5, "bep_flow_rate": 1750.0, "bep_deviation_pct": -17.1}
    raw_models = {"degradation_probability": 0.72, "predicted_fault_class": "Gas Interference"}

    compact = builder.build(
        asset_id="FS-031",
        objective_id="OP01_PRODUCTION_DECLINE",
        telemetry=raw_telemetry,
        engineering=raw_engineering,
        model_outputs=raw_models,
        evidence_refs=["EV-001", "EV-007", "EV-013"],
        safety_constraints=["ADVISORY-ONLY"],
    )

    assert compact["asset_id"] == "FS-031"
    assert compact["objective"] == "OP01_PRODUCTION_DECLINE"
    assert "telemetry_summary" in compact
    assert compact["telemetry_summary"]["flow"]["trend"] == "declining"
    assert compact["engineering"]["tdh_ft"] == 4042.5
    assert compact["ml_scores"]["degradation_probability"] == 0.72
    assert "EV-001" in compact["frozen_evidence_ids"]

    # Ensure JSON representation is under 800 characters (token-friendly)
    serialized = json.dumps(compact)
    assert len(serialized) < 1500


# ---------------------------------------------------------------------------
# Test 3: Layered Prompt Builder Composition
# ---------------------------------------------------------------------------
def test_3_layered_prompt_builder():
    compact = {
        "asset_id": "FS-031",
        "objective": "OP01_PRODUCTION_DECLINE",
        "telemetry_summary": {"flow": {"current": 735.7, "trend": "declining"}},
    }

    messages = LayeredPromptBuilder.build_chat_messages(
        compact_context=compact,
        user_query="Why is head declining on FS-031?",
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "Agent Jane" in messages[0]["content"]
    assert "ESP DOMAIN DIAGNOSTIC RULES" in messages[0]["content"]

    assert messages[1]["role"] == "user"
    assert "OBJECTIVE: Root Cause Analysis for ESP Production Decline." in messages[1]["content"]
    assert "FS-031" in messages[1]["content"]
    assert "OUTPUT REQUIREMENT:" in messages[1]["content"]


# ---------------------------------------------------------------------------
# Test 4: Pydantic Structured Output Validation & Repair Loop
# ---------------------------------------------------------------------------
def test_4_structured_output_repair_loop():
    validator = StructuredOutputValidator(AdvisoryOutputSchema)

    # 1. Valid raw JSON
    valid_raw = json.dumps({
        "assessment": "Gas slugging detected at pump intake.",
        "hypotheses": [
            {
                "cause": "Intake Gas Interference",
                "confidence": 0.82,
                "supporting_evidence": ["EV-001"],
                "contradicting_evidence": []
            }
        ],
        "uncertainties": [],
        "recommendation": "Execute gas purge cycle.",
        "verification": "Inspect PIP sensor log."
    })

    parsed = validator.parse(valid_raw)
    assert isinstance(parsed, AdvisoryOutputSchema)
    assert parsed.hypotheses[0].cause == "Intake Gas Interference"
    assert parsed.hypotheses[0].confidence == 0.82

    # 2. Repair loop simulation: first response is malformed JSON, second response is fixed
    malformed_raw = "Here is my diagnosis: {assessment: missing_quotes}"
    repairs_counter = [0]

    def mock_repair_callback(repair_prompt: str) -> str:
        repairs_counter[0] += 1
        return valid_raw

    fixed = validator.parse_with_repair(malformed_raw, mock_repair_callback)
    assert isinstance(fixed, AdvisoryOutputSchema)
    assert repairs_counter[0] == 1


# ---------------------------------------------------------------------------
# Test 5: XAI Visual Story Engine Builder
# ---------------------------------------------------------------------------
def test_5_xai_visual_story_builder():
    xai_builder = XAIVisualStoryBuilder()
    advisory = AdvisoryOutputSchema(
        assessment="High-frequency intake pressure fluctuations indicate gas interference.",
        hypotheses=[
            {
                "cause": "Intake Gas Interference",
                "confidence": 0.88,
                "supporting_evidence": ["EV-001", "EV-007"],
                "contradicting_evidence": []
            }
        ],
        uncertainties=["GOR measurement timestamp unverified"],
        recommendation="Initiate automated gas separator purge.",
        verification="Inspect physical wellhead pressure gauge."
    )
    compact_context = {"asset_id": "FS-031", "objective": "OP01_PRODUCTION_DECLINE"}

    xai_exp = xai_builder.build(advisory, compact_context)

    assert isinstance(xai_exp, XAIExplanationPayload)
    assert xai_exp.primary_hypothesis == "Intake Gas Interference"
    assert xai_exp.confidence == 0.88
    assert len(xai_exp.visualizations) >= 2

    # Check visualization cards
    card_ids = [v.card_id for v in xai_exp.visualizations]
    assert "telemetry" in card_ids
    assert "pump_curve" in card_ids
    assert "diagnosis" in card_ids


# ---------------------------------------------------------------------------
# Test 6: LLM Observability & Audit Tracing
# ---------------------------------------------------------------------------
def test_6_llm_observability_tracer():
    local_tracer = LLMObservabilityTracer()
    record = LLMTraceRecord(
        run_id="RUN-TEST-100",
        agent_id="AgentJane",
        objective_id="OP01_PRODUCTION_DECLINE",
        model_name="qwen2.5:3b-mock",
        prompt_tokens=150,
        completion_tokens=80,
        total_tokens=230,
        latency_ms=12.5,
        is_mock=True,
        validation_passed=True,
        repair_attempts=0,
    )

    local_tracer.record_trace(record)

    traces = local_tracer.get_traces_for_run("RUN-TEST-100")
    assert len(traces) == 1
    assert traces[0].total_tokens == 230
    assert traces[0].latency_ms == 12.5

    stats = local_tracer.get_summary_stats()
    assert stats["total_calls"] == 1
    assert stats["total_tokens"] == 230


# ---------------------------------------------------------------------------
# Test 7: LLM Adapter End-to-End & Supervisor Graph Wiring
# ---------------------------------------------------------------------------
def test_7_llm_adapter_end_to_end():
    gw = LLMGateway(offline_mode=True)
    adapter = LLMAdapter(gateway=gw)

    compact_ctx = {
        "asset_id": "FS-031",
        "objective": "OP01_PRODUCTION_DECLINE",
        "telemetry_summary": {"flow": {"current": 1450.0, "trend": "declining"}},
    }

    advisory, xai_exp = adapter.generate_advisory_from_compact_context(
        compact_context=compact_ctx,
        user_query="Jane, why is FS-031 producing less liquid?",
        run_id="RUN-E2E-101",
    )

    assert isinstance(advisory, AdvisoryOutputSchema)
    assert isinstance(xai_exp, XAIExplanationPayload)
    assert len(advisory.hypotheses) > 0

    # Test integration into UserEntryAdapter / Supervisor Graph
    entry = UserEntryAdapter()
    result_advisory = entry.run(
        user_query="Jane, analyze production decline for FS-031",
        asset_id="FS-031",
        request_id="REQ-PHASE10-E2E",
    )

    assert result_advisory.asset_id == "FS-031"
    assert result_advisory.advisory_id == "ADV-REQ-PHASE10-E2E"
    assert "Supervisor Orchestrator v7.0 (LLM Phase 10)" in result_advisory.provenance
