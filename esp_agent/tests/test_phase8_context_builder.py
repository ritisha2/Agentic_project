"""
Unit Test Suite for ContextBuilder & EvidenceFreezeManager (Step 2)
"""

import pytest
from src.services.evidence.context_builder import ContextBuilder
from src.services.evidence.freeze_manager import EvidenceFreezeManager


def test_1_build_and_freeze_evidence_pack():
    builder = ContextBuilder()
    pack = builder.build_evidence_pack(
        request_id="REQ-001",
        asset_id="FS-031",
        objective_id="OP02_PRODUCTION_DECLINE_RCA",
        telemetry_data={"flowline_pressure": 350.0, "motor_temp": 110.0},
        calculations={"calculate_tdh": 4042.5},
        model_outputs={"fault_classifier": {"identified_fault": "Intake Gas Interference", "confidence": 0.88}}
    )

    assert pack.frozen is True
    assert pack.checksum is not None
    assert EvidenceFreezeManager.verify_integrity(pack) is True
    assert len(pack.items) >= 4


def test_2_build_context_view():
    builder = ContextBuilder()
    pack = builder.build_evidence_pack(
        request_id="REQ-002",
        asset_id="FS-031",
        objective_id="OP02_PRODUCTION_DECLINE_RCA",
        telemetry_data={"pip": 350.0}
    )

    view = builder.build_context_view(pack, run_id="RUN-002")
    assert view.run_id == "RUN-002"
    assert view.evidence_pack_id == pack.pack_id
    assert "pip" in view.current_state
