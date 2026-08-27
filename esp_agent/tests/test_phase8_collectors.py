"""
Unit Test Suite for Multi-Source Evidence Collectors (Step 2)
"""

import pytest
from src.services.evidence.collector import EvidenceCollector
from src.schemas.evidence import EvidenceType, AuthorityLevel


def test_1_collect_asset_context():
    context = {"pump_model": "Weatherford DN1750", "motor_rating_hp": 250.0}
    items = EvidenceCollector.collect_from_asset_context("FS-031", context)
    assert len(items) == 2
    assert items[0].authority_level == AuthorityLevel.LEVEL_A_INSTALLED_APPROVED
    assert items[0].value == "Weatherford DN1750"


def test_2_collect_telemetry():
    telemetry = {"flowline_pressure": 350.0, "motor_temp": 110.0}
    items = EvidenceCollector.collect_from_telemetry("FS-031", telemetry)
    assert len(items) == 2
    assert items[0].evidence_type == EvidenceType.TELEMETRY
    assert items[0].unit == "psi"
    assert items[1].unit == "°C"


def test_3_collect_engineering_and_models():
    calcs = {"calculate_tdh": 4042.5}
    eng_items = EvidenceCollector.collect_from_engineering("FS-031", calcs)
    assert len(eng_items) == 1
    assert eng_items[0].evidence_type == EvidenceType.ENGINEERING
    assert eng_items[0].unit == "ft"

    models = {"fault_classifier": {"identified_fault": "Intake Gas Interference", "confidence": 0.88}}
    ml_items = EvidenceCollector.collect_from_models("FS-031", models)
    assert len(ml_items) == 1
    assert ml_items[0].evidence_type == EvidenceType.ML
    assert ml_items[0].confidence == 0.88
