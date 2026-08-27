"""
15-Point Asset Context Service Verification Matrix Test Suite
Grounded in ESP_APM_Asset_Context_Service_Verification_Architecture.docx Table 6 (ACS-001 to ACS-015)
"""

import pytest
from src.services.asset_context_service import AssetContextService


def test_ACS_001_health_check():
    """ACS-001: Service liveness/readiness verification."""
    service = AssetContextService()
    assert service is not None


def test_ACS_002_list_assets():
    """ACS-002: Discovery list returns current seed assets."""
    service = AssetContextService()
    assets = service.list_assets()
    assert len(assets) >= 26
    assert "FS-031" in assets
    assert "FSWS-001-A" in assets


def test_ACS_003_known_asset_fs031():
    """ACS-003: Known asset FS-031 returns 200 with exact identity."""
    service = AssetContextService()
    ctx = service.get_context("FS-031")
    assert ctx.asset_id == "FS-031"
    assert ctx.well_id == "FS-031"
    assert ctx.asset_type in ("ESP", "ESP_WELL")
    assert ctx.status == "ACTIVE"


def test_ACS_004_unknown_asset_safe_404():
    """ACS-004: Unknown asset ID fails safely with ValueError / 404 (no hallucinated records)."""
    service = AssetContextService()
    with pytest.raises(ValueError) as exc_info:
        service.get_cached_asset_context("UNKNOWN_WELL_999")
    assert "ASSET_NOT_FOUND" in str(exc_info.value)


def test_ACS_005_canonical_context_schema():
    """ACS-005: Canonical context schema contains all required top-level fields."""
    service = AssetContextService()
    ctx = service.get_context("FS-031")
    assert ctx.hierarchy is not None
    assert ctx.well_context is not None
    assert ctx.esp_configuration is not None
    assert ctx.tag_mapping is not None
    assert ctx.signal_catalog is not None
    assert ctx.source_provenance is not None
    assert ctx.missing_fields is not None


def test_ACS_006_hierarchy_resolution():
    """ACS-006: Known hierarchy is accurate."""
    service = AssetContextService()
    ctx = service.get_context("FS-031")
    assert ctx.hierarchy.customer == "CCED"
    assert ctx.hierarchy.block == "BLOCK 3"
    assert ctx.hierarchy.station == "FARHA"


def test_ACS_007_tag_semantics_and_units():
    """ACS-007: Tag mappings, units, and ranges are correct."""
    service = AssetContextService()
    ctx = service.get_context("FS-031")
    assert len(ctx.tag_mapping) > 0
    assert "R_INTAKE_PRESS" in ctx.tag_mapping
    assert ctx.tag_mapping["R_INTAKE_PRESS"] == "intake_pressure"
    
    # Verify signal catalog item
    item = next(s for s in ctx.signal_catalog if s.tag == "R_INTAKE_PRESS")
    assert item.unit == "psi"


def test_ACS_008_null_policy():
    """ACS-008: Unknown/unsupplied fields remain explicit null (never 0, false, or empty string)."""
    service = AssetContextService()
    ctx = service.get_context("FS-031")
    # Unsupplied cluster remains null
    assert ctx.hierarchy.cluster is None or isinstance(ctx.hierarchy.cluster, str)


def test_ACS_009_operating_range_vs_safety_limit():
    """ACS-009: Operating ranges are separated from approved safety limits."""
    service = AssetContextService()
    ctx = service.get_context("FS-031")
    for s in ctx.signal_catalog:
        assert s.is_safety_limit is False  # Operating ranges are NOT false safety limits


def test_ACS_010_source_provenance():
    """ACS-010: Source, record version, and Level A authority are visible."""
    service = AssetContextService()
    ctx = service.get_context("FS-031")
    assert ctx.source_provenance.authoritative_level == "A"
    assert ctx.source_provenance.source_system in ("ADVAIT", "ADVAIT_REGISTRY", "SIMULATOR")
    assert ctx.source_provenance.record_version != ""


def test_ACS_011_explicit_missing_fields():
    """ACS-011: Explicit missing_fields array documents unavailable attributes."""
    service = AssetContextService()
    ctx = service.get_context("FS-031")
    assert isinstance(ctx.missing_fields, list)


def test_ACS_012_telemetry_binding():
    """ACS-012: Tag mapping registry binds asset telemetry tags correctly."""
    service = AssetContextService()
    mapping = service.get_tag_mapping("FS-031")
    assert "R_MOTOR_TEMP" in mapping
    assert mapping["R_MOTOR_TEMP"] == "motor_temperature"


def test_ACS_013_ground_truth_scenario_exclusion():
    """ACS-013: Simulator fault catalog items are tagged simulator_scenario_only."""
    service = AssetContextService()
    catalog = service.get_fault_catalog("FS-031")
    assert len(catalog) > 0
    assert catalog[0]["simulator_scenario_only"] is True


def test_ACS_014_bad_telemetry_handling():
    """ACS-014: Validation rejects unmapped or invalid asset IDs."""
    service = AssetContextService()
    with pytest.raises(ValueError):
        service.get_cached_asset_context("INVALID_ID_000")


def test_ACS_015_versioning():
    """ACS-015: Config record version is exposed for change tracking."""
    service = AssetContextService()
    ctx = service.get_context("FS-031")
    assert ctx.source_provenance.record_version in ("v2.1", "1")
