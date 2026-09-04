"""
Unit Test Suite for Conflict Detection & Ranking (Step 2)
"""

import pytest
from src.schemas.evidence import EvidenceItem, EvidenceType, AuthorityLevel, QualityStatus
from src.services.evidence.conflict_engine import ConflictEngine
from src.services.evidence.ranker import EvidenceRanker


def test_1_conflict_detection_ml_vs_physics():
    ml_item = EvidenceItem(
        evidence_id="ML-1", evidence_type=EvidenceType.ML, asset_id="FS-031",
        source_system="ModelAdapter", source_id="fault_classifier", timestamp="2026-08-26T12:00:00Z",
        observed_at="2026-08-26T12:00:00Z", authority_level=AuthorityLevel.LEVEL_D_SITE_HISTORY,
        value="Intake Gas Interference", statement="ML predicts Gas Interference"
    )
    eng_item = EvidenceItem(
        evidence_id="ENG-1", evidence_type=EvidenceType.ENGINEERING, asset_id="FS-031",
        source_system="EngineeringService", source_id="calculate_tdh", timestamp="2026-08-26T12:00:00Z",
        observed_at="2026-08-26T12:00:00Z", authority_level=AuthorityLevel.LEVEL_C_CUSTOMER_ENG,
        value="Normal Head", statement="TDH calculation shows normal head"
    )

    conflicts = ConflictEngine.detect_conflicts([ml_item, eng_item])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "ML_VS_PHYSICS"


def test_2_evidence_ranker():
    item1 = EvidenceItem(
        evidence_id="1", evidence_type=EvidenceType.TELEMETRY, asset_id="FS-031",
        source_system="Telemetry", source_id="pip", timestamp="2026-08-26T12:00:00Z",
        observed_at="2026-08-26T12:00:00Z", authority_level=AuthorityLevel.LEVEL_A_INSTALLED_APPROVED,
        quality_status=QualityStatus.GOOD, relevance_score=1.0, confidence=1.0, statement="Good telemetry"
    )
    item2 = EvidenceItem(
        evidence_id="2", evidence_type=EvidenceType.TELEMETRY, asset_id="FS-031",
        source_system="Telemetry", source_id="pip_stale", timestamp="2026-08-26T12:00:00Z",
        observed_at="2026-08-26T12:00:00Z", authority_level=AuthorityLevel.LEVEL_E_INDUSTRY,
        quality_status=QualityStatus.STALE, relevance_score=0.5, confidence=0.5, statement="Stale industry prior"
    )

    ranked = EvidenceRanker.rank_items([item2, item1])
    assert ranked[0].evidence_id == "1"


def test_3_conflict_detection_kb_limit_discrepancy():
    """If Takacs manual says 140°C but API RP 11S says 150°C, generate KB_LIMIT_DISCREPANCY and override."""
    takacs_item = EvidenceItem(
        evidence_id="KB-TAKACS-1", evidence_type=EvidenceType.KNOWLEDGE, asset_id="FS-031",
        source_system="RetrievalService", source_id="Takacs_ESP_Manual", timestamp="2026-08-26T12:00:00Z",
        observed_at="2026-08-26T12:00:00Z", authority_level=AuthorityLevel.LEVEL_E_INDUSTRY,
        semantic_type="motor_temperature_limit", value=140.0, unit="°C",
        statement="Motor maximum continuous temperature limit is 140 °C."
    )
    api_item = EvidenceItem(
        evidence_id="KB-API-1", evidence_type=EvidenceType.KNOWLEDGE, asset_id="FS-031",
        source_system="RetrievalService", source_id="API_RP_11S8", timestamp="2026-08-26T12:00:00Z",
        observed_at="2026-08-26T12:00:00Z", authority_level=AuthorityLevel.LEVEL_A_INSTALLED_APPROVED,
        semantic_type="motor_temperature_limit", value=150.0, unit="°C",
        statement="API RP 11S8 mandates critical motor temperature trip at 150.0 °C."
    )

    conflicts = ConflictEngine.detect_conflicts([takacs_item, api_item])
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.conflict_type == "KB_LIMIT_DISCREPANCY"
    assert "LEVEL_A_INSTALLED_APPROVED (API_RP_11S8) > LEVEL_E_INDUSTRY (Takacs_ESP_Manual)" in c.authority_comparison
    assert c.resolution_status == "RESOLVED"
    assert "overrides" in c.resolution_method
