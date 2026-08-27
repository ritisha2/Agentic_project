"""
Unit Test Suite for Evidence Freeze & Provenance Repository (Step 3)
"""

import pytest
from src.adapters.evidence_repository import EvidenceRepository
from src.services.evidence.context_builder import ContextBuilder
from src.services.evidence.freeze_manager import EvidenceFreezeManager


def test_1_evidence_repository_save_and_retrieve():
    repo = EvidenceRepository()
    builder = ContextBuilder()

    pack = builder.build_evidence_pack(
        request_id="REQ-REPO-01",
        asset_id="FS-031",
        objective_id="OP02_PRODUCTION_DECLINE_RCA",
        telemetry_data={"pip": 350.0}
    )

    pack_id = repo.save_evidence_pack(pack)
    assert pack_id == pack.pack_id

    retrieved_pack = repo.get_evidence_pack(pack_id)
    assert retrieved_pack is not None
    assert retrieved_pack.checksum == pack.checksum
    assert EvidenceFreezeManager.verify_integrity(retrieved_pack) is True

    # Check individual item lookup
    if pack.items:
        first_item = repo.get_evidence_item(pack.items[0].evidence_id)
        assert first_item is not None
        assert first_item.evidence_id == pack.items[0].evidence_id
