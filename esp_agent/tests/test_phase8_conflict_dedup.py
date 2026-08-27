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
