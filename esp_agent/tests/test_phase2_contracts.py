"""
Phase 2 External Contracts Integration Test Suite
Validates schema serialization, contract consistency, and service adapters for Phase 2.
"""

import yaml
import pytest
from src.schemas.contracts import (
    AssetContextPayload, TelemetryPayload, TelemetryMetric,
    ModelOutputPayload, RuleStatusPayload, RuleDeviationCounts,
    AnomalyResultPayload, FailurePredictionPayload, FaultDiagnosisPayload,
    HealthIndexPayload
)
from src.adapters.asset_service import AssetService
from src.adapters.model_adapter import ModelAdapter

def test_1_asset_contract_schema():
    asset_service = AssetService()
    asset: AssetContextPayload = asset_service.get_asset("ESP-Well-001")
    
    assert asset.asset_id == "ESP-Well-001"
    assert asset.well_id == "WELL-001"
    assert asset.pump_model == "Weatherford DN1750"
    assert asset.motor_rating_hp == 250.0
    assert asset.be_point_bpd == 1750.0
    assert asset.source_system in ("ADVAIT_CACHE", "ADVAIT_CACHE_FALLBACK", "ADVAIT_REGISTRY")

def test_2_telemetry_contract_schema():
    metric = TelemetryMetric(
        tag="motor_temperature",
        value=135.0,
        unit="°C",
        timestamp="2026-08-25T12:00:00Z",
        quality="GOOD"
    )
    payload = TelemetryPayload(
        asset_id="ESP-Well-001",
        timestamp="2026-08-25T12:00:00Z",
        metrics={"motor_temperature": metric},
        data_quality_summary="GOOD"
    )
    assert payload.asset_id == "ESP-Well-001"
    assert payload.metrics["motor_temperature"].value == 135.0
    assert payload.metrics["motor_temperature"].unit == "°C"

def test_3_model_output_contract_schema():
    model_adapter = ModelAdapter()
    output: ModelOutputPayload = model_adapter.get_model_output("ESP-Well-001", {"motor_temperature": 135.0})
    
    assert output.asset_id == "ESP-Well-001"
    assert output.rules.deviation_counts.h24 == 5
    assert output.anomaly.anomaly_score == 0.91
    assert output.failure.risk_24h == 0.72
    assert output.failure.rul_hours == 75.0
    assert output.fault.predicted_fault_class == "MOTOR_OVERHEATING"
    assert output.health.health_index == 45
    assert "fault_classifier" in output.model_versions

def test_4_model_kb_fault_taxonomy_contract_consistency():
    import os
    candidate_paths = [
        "../esp-knowledge/deterministic/faults/seed_faults.yaml",
        "esp-knowledge/deterministic/faults/seed_faults.yaml",
        "x:/TAS/Agentic_project/esp-knowledge/deterministic/faults/seed_faults.yaml"
    ]
    
    yaml_path = None
    for p in candidate_paths:
        if os.path.exists(p):
            yaml_path = p
            break
            
    assert yaml_path is not None, "seed_faults.yaml file not found in candidate paths!"

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    kb_fault_codes = {item.get("fault_id", item.get("fault_code")) for item in data["faults"]}
    
    model_adapter = ModelAdapter()
    is_valid = model_adapter.validate_model_fault_taxonomy_contract(kb_fault_codes)
    
    assert is_valid is True, "Model predicted fault classes must match KB fault taxonomy!"
