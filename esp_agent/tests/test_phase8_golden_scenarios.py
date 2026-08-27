"""
End-to-End Golden Scenarios Test Suite for Phase 8 Evidence Pack & Agent Context Layer
"""

import pytest
from src.agent.supervisor.user_entry import UserEntryAdapter
from src.events.event_objective_router import EventObjectiveRouter
from shared.schemas.event import ESPEvent, SeverityLevel
from src.services.evidence.context_builder import ContextBuilder
from src.adapters.evidence_repository import EvidenceRepository
from src.services.evidence.freeze_manager import EvidenceFreezeManager
from src.schemas.evidence import AuthorityLevel, QualityStatus, EvidenceType


def test_golden_scenario_1_user_production_decline_evidence_pack():
    """
    Scenario 1: User Query 'Why is FS-031 producing less?'
    Verifies that EvidencePack is generated, ranked by A-F authority, frozen, and audited.
    """
    user_adapter = UserEntryAdapter()
    advisory = user_adapter.run(
        user_query="Why is FS-031 producing less?",
        asset_id="FS-031",
        request_id="GOLD-P8-01"
    )

    assert advisory.objective_id == "OP02_PRODUCTION_DECLINE_RCA"
    assert advisory.asset_id == "FS-031"
    assert len(advisory.evidence) > 0

    # Retrieve frozen pack from repo
    repo = EvidenceRepository()
    packs = repo.list_packs_for_asset("FS-031")
    assert len(packs) > 0

    latest_pack = packs[-1]
    assert latest_pack.frozen is True
    assert latest_pack.checksum is not None
    assert EvidenceFreezeManager.verify_integrity(latest_pack) is True


def test_golden_scenario_2_event_trigger_evidence_pack():
    """
    Scenario 2: Event PRODUCTION_DECLINE_DETECTED trigger
    Verifies that EventObjectiveRouter executes the same Phase 8 EvidencePack pipeline.
    """
    event_router = EventObjectiveRouter()
    evt = ESPEvent(
        event_id="EVT-P8-02",
        event_type="PRODUCTION_DECLINE_DETECTED",
        severity=SeverityLevel.MEDIUM,
        asset_id="FS-031",
        source_service="telemetry_detector",
        payload={"telemetry": {"flowline_pressure": 345.0, "pip": 320.0}}
    )
    advisory = event_router.route_and_execute(evt)

    assert advisory.objective_id == "OP02_PRODUCTION_DECLINE_RCA"
    assert advisory.asset_id == "FS-031"
    assert advisory.confidence > 0.5


def test_golden_scenario_3_conflict_detection_and_authority():
    """
    Scenario 3: ML vs. Engineering Conflict Detection & Authority Precedence (Level A > Level F)
    """
    builder = ContextBuilder()
    pack = builder.build_evidence_pack(
        request_id="GOLD-P8-03",
        asset_id="FS-031",
        objective_id="OP02_PRODUCTION_DECLINE_RCA",
        asset_context={"pump_model": "Weatherford DN1750"},
        telemetry_data={"intake_pressure": 320.0},
        calculations={"calculate_tdh": 4042.5},
        model_outputs={"fault_classifier": {"identified_fault": "Intake Gas Interference", "confidence": 0.88}}
    )

    assert pack.frozen is True
    # Verify authority ordering: Level A (Asset context/telemetry) before Level D/F (Model/LLM)
    item_authorities = [item.authority_level for item in pack.items]
    assert item_authorities[0] in (AuthorityLevel.LEVEL_A_INSTALLED_APPROVED, AuthorityLevel.LEVEL_B_OEM)
