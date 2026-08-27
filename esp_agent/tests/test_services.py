"""
Unit and Integration Tests for RetrievalService and ContextBuilder
"""

import pytest
from src.services.retrieval_service import RetrievalService
from src.services.context_builder import ContextBuilder

def test_retrieval_service_glossary():
    service = RetrievalService()
    res = service.search_glossary("ROR")
    assert res is not None
    assert res["term_id"] == "ROR"
    assert "Recommended Operating Range" in res["preferred_name"]

def test_retrieval_service_fault_taxonomy():
    service = RetrievalService()
    res = service.search_fault_taxonomy("MOTOR_OVERHEATING")
    assert len(res) > 0
    assert res[0]["fault_id"] == "MOTOR_OVERHEATING"
    assert res[0]["category"] == "THERMAL"

def test_retrieval_service_hybrid_retrieve():
    service = RetrievalService()
    res = service.hybrid_retrieve("What causes gas lock in an ESP?")
    assert res["retrieval_status"] == "SUCCESS"
    assert len(res["vector_results"]) > 0

def test_context_builder_evidence_pack():
    builder = ContextBuilder()
    telemetry = {
        "primary_thermal_metric": 135.0,
        "primary_intake_pressure": 120.0
    }
    models = {
        "fault_classifier": {"identified_fault": "MOTOR_OVERHEATING", "confidence": 0.88}
    }
    calcs = {
        "TDH_Calculation": 4500.0
    }
    
    pack = builder.build_evidence_pack(
        request_id="REQ-001",
        asset_id="ESP-Well-001",
        objective_id="DIAGNOSE_FAULT",
        user_query="Why is ESP-Well-001 overheating?",
        telemetry_data=telemetry,
        model_outputs=models,
        calculations=calcs
    )
    
    assert pack.asset_id == "ESP-Well-001"
    assert pack.data_quality_summary in ["COMPLETE", "PARTIAL"]
    assert len(pack.telemetry_evidence) == 2
    assert len(pack.model_evidence) == 1
    assert len(pack.calculation_evidence) == 1

def test_context_builder_prompt_overlay():
    builder = ContextBuilder()
    pack = builder.build_evidence_pack(
        request_id="REQ-002",
        asset_id="ESP-Well-001",
        objective_id="DIAGNOSE_FAULT",
        user_query="Check status",
        telemetry_data={"primary_thermal_metric": 135.0}
    )
    overlay = builder.format_llm_prompt_overlay(pack)
    assert "EVIDENCE PACK" in overlay
    assert "LIVE TELEMETRY READINGS" in overlay
    assert "135.0" in overlay
