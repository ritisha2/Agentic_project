"""
Unit Test Suite for XAI & Visual Story Engine (Step 1)
"""

import pytest
from src.services.evidence.context_builder import ContextBuilder
from src.services.xai_service import XAIEngine, XAIExplanationPayload, VisualStorySpec


def test_1_xai_explanation_generation():
    builder = ContextBuilder()
    pack = builder.build_evidence_pack(
        request_id="REQ-XAI-01",
        asset_id="FS-031",
        objective_id="OP02_PRODUCTION_DECLINE_RCA",
        telemetry_data={"flowline_pressure": 350.0},
        calculations={"calculate_tdh": 4042.5},
        model_outputs={"fault_classifier": {"identified_fault": "Intake Gas Interference", "confidence": 0.88}}
    )

    advisory = {
        "diagnosis": "Intake Gas Interference probable",
        "confidence": 0.88
    }

    explanation = XAIEngine.generate_explanation(pack, advisory)
    assert explanation.asset_id == "FS-031"
    assert len(explanation.visual_stories) >= 2
    assert explanation.supporting_evidence_count >= 3
    assert len(explanation.counterfactuals) > 0
    assert "AssetContextService" in explanation.source_contributions or "TelemetryService" in explanation.source_contributions
