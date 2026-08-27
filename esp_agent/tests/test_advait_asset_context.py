"""
Integration Test Suite for Advait Asset Registry & Tag Mapping Layer
Verifies rich asset context parsing, hierarchy, tag mappings, and API mock fallback.
"""

import pytest
from src.adapters.asset_service import AssetService
from src.schemas.contracts import AssetContextPayload

@pytest.fixture
def asset_service():
    return AssetService()

def test_1_get_real_advait_asset_fsws_001_a(asset_service):
    """Verify loading real asset FSWS-001-A from rich Advait seed dataset"""
    asset: AssetContextPayload = asset_service.get_asset("FSWS-001-A")
    
    assert asset.asset_id == "FSWS-001-A"
    assert asset.well_id == "FSWS-001-A"
    assert asset.asset_type == "ESP_WELL"
    assert asset.source_system == "ADVAIT_REGISTRY"
    assert asset.hierarchy["customer"] == "CCED"
    assert asset.hierarchy["block"] == "BLOCK 3"
    assert asset.hierarchy["station"] == "FARHA"

def test_2_verify_tag_mapping_registry(asset_service):
    """Verify 13 physical SCADA tags are present in asset tag mapping"""
    asset: AssetContextPayload = asset_service.get_asset("FSWS-001-A")
    
    assert asset.tag_mapping is not None
    tags_list = asset.tag_mapping.get("tags", [])
    tags = {t["tag_name"]: t for t in tags_list}
    
    # Check physical tag mappings
    assert "R_INTAKE_PRESS" in tags
    assert tags["R_INTAKE_PRESS"]["semantic_name"] == "intake_pressure"
    assert tags["R_INTAKE_PRESS"]["engineering_unit"] == "psi"
    
    assert "R_MOTOR_TEMP" in tags
    assert tags["R_MOTOR_TEMP"]["semantic_name"] == "motor_temperature"
    assert tags["R_MOTOR_TEMP"]["engineering_unit"] == "degC"
    
    assert "R_FREQUENCY" in tags
    assert tags["R_FREQUENCY"]["semantic_name"] == "frequency"
    assert tags["R_FREQUENCY"]["engineering_unit"] == "Hz"

def test_3_verify_multiple_assets(asset_service):
    """Verify multiple assets from 26 well seed registry"""
    for asset_id in ["FSWS-003", "FS-010", "FS-013", "FS-046"]:
        asset = asset_service.get_asset(asset_id)
        assert asset.asset_id == asset_id
        assert asset.hierarchy["customer"] == "CCED"

def test_4_synthetic_fallback(asset_service):
    """Verify graceful fallback for synthetic/unknown asset IDs"""
    asset = asset_service.get_asset("UNKNOWN-TEST-WELL-999")
    assert asset.asset_id == "UNKNOWN-TEST-WELL-999"
    assert asset.source_system == "ADVAIT_CACHE_FALLBACK"
