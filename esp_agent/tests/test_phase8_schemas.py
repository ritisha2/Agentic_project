"""
Unit Test Suite for Phase 8 Schemas (EvidenceItem, EvidenceConflict, EvidencePack, ContextView)
"""

import pytest
from src.schemas.evidence import (
    EvidenceType, AuthorityLevel, QualityStatus, EvidenceItem,
    EvidenceConflict, EvidencePack
)
from src.schemas.context_view import ContextView


def test_1_evidence_item_creation():
    item = EvidenceItem(
        evidence_id="EVID-TEL-001",
        evidence_type=EvidenceType.TELEMETRY,
        asset_id="FS-031",
        source_system="TelemetryAdapter",
        source_id="flowline_pressure",
        timestamp="2026-08-26T12:00:00Z",
        observed_at="2026-08-26T12:00:00Z",
        authority_level=AuthorityLevel.LEVEL_A_INSTALLED_APPROVED,
        quality_status=QualityStatus.GOOD,
        value=350.0,
        unit="psi",
        statement="Flowline pressure reading is 350.0 psi"
    )
    assert item.evidence_id == "EVID-TEL-001"
    assert item.authority_level == AuthorityLevel.LEVEL_A_INSTALLED_APPROVED
    assert item.quality_status == QualityStatus.GOOD


def test_2_evidence_conflict_creation():
    conflict = EvidenceConflict(
        conflict_id="CONF-001",
        evidence_refs=["EVID-ML-001", "EVID-ENG-001"],
        conflict_type="ML_VS_PHYSICS",
        values={"ML": "Intake Gas Interference", "Engineering": "Gas Lock Probable"},
        authority_comparison="Engineering Calculation (Level C) > ML Model (Level D)",
        impact="HIGH",
        resolution_status="SURFACED"
    )
    assert conflict.conflict_id == "CONF-001"
    assert conflict.conflict_type == "ML_VS_PHYSICS"


def test_3_evidence_pack_and_context_view():
    pack = EvidencePack(
        pack_id="PACK-001",
        request_id="REQ-001",
        asset_id="FS-031",
        objective_id="OP02_PRODUCTION_DECLINE_RCA",
        created_at="2026-08-26T12:00:00Z",
        frozen=True,
        checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    assert pack.frozen is True
    assert pack.checksum is not None

    view = ContextView(
        run_id="RUN-001",
        objective_id="OP02_PRODUCTION_DECLINE_RCA",
        evidence_pack_id="PACK-001",
        missing_data=["motor_vibration"]
    )
    assert view.run_id == "RUN-001"
    assert "motor_vibration" in view.missing_data
