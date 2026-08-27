"""
Unit Test Suite for Authority Precedence & QoD Validation (Step 2)
"""

import time
import pytest
from src.schemas.evidence import EvidenceItem, EvidenceType, AuthorityLevel, QualityStatus
from src.services.evidence.authority_engine import AuthorityEngine
from src.services.evidence.qod_validator import QoDValidator


def test_1_authority_level_ordering():
    item_level_a = EvidenceItem(
        evidence_id="1", evidence_type=EvidenceType.ASSET, asset_id="FS-031",
        source_system="AssetContext", source_id="pump", timestamp="2026-08-26T12:00:00Z",
        observed_at="2026-08-26T12:00:00Z", authority_level=AuthorityLevel.LEVEL_A_INSTALLED_APPROVED,
        statement="Installed pump specs"
    )
    item_level_f = EvidenceItem(
        evidence_id="2", evidence_type=EvidenceType.KNOWLEDGE, asset_id="FS-031",
        source_system="LLM", source_id="prior", timestamp="2026-08-26T12:00:00Z",
        observed_at="2026-08-26T12:00:00Z", authority_level=AuthorityLevel.LEVEL_F_LLM_PRIOR,
        statement="LLM prior guess"
    )

    sorted_items = AuthorityEngine.resolve_precedence([item_level_f, item_level_a])
    assert sorted_items[0].authority_level == AuthorityLevel.LEVEL_A_INSTALLED_APPROVED
    assert sorted_items[1].authority_level == AuthorityLevel.LEVEL_F_LLM_PRIOR


def test_2_qod_freshness_evaluation():
    old_iso = "2026-08-01T12:00:00Z"  # ~25 days old
    stale_item = EvidenceItem(
        evidence_id="3", evidence_type=EvidenceType.TELEMETRY, asset_id="FS-031",
        source_system="Telemetry", source_id="pip", timestamp=old_iso,
        observed_at=old_iso, quality_status=QualityStatus.GOOD, statement="Old telemetry"
    )

    status = QoDValidator.evaluate_item_qod(stale_item, objective_id="OP02_PRODUCTION_DECLINE_RCA")
    assert status == QualityStatus.STALE
