"""
Unit Tests for Event Schemas and Taxonomy
Grounded in Phase 6 Event-Driven Architecture Spec §5, §7
"""

import os
import yaml
import pytest
from shared.schemas.event import ESPEvent, SeverityLevel
from shared.schemas.event_payloads import FailureRiskPayload, TripEventPayload


def test_espevent_instantiation_and_defaults():
    """Verify ESPEvent Pydantic model serialization and defaults."""
    evt = ESPEvent(
        event_id="EVT-001",
        event_type="FAILURE_RISK_INCREASED",
        asset_id="FS-031",
        source_service="failure-risk-model",
        severity=SeverityLevel.HIGH,
        payload={"risk_7d": 0.75, "previous_risk_7d": 0.40}
    )
    assert evt.event_id == "EVT-001"
    assert evt.tenant_id == "CCED"
    assert evt.severity == SeverityLevel.HIGH
    assert evt.payload["risk_7d"] == 0.75

    # Roundtrip dump and reload
    data = evt.model_dump()
    reloaded = ESPEvent(**data)
    assert reloaded.event_id == evt.event_id
    assert reloaded.severity == SeverityLevel.HIGH


def test_event_taxonomy_yaml_validity():
    """Verify event_taxonomy.yaml exists and parses cleanly."""
    tax_path = "knowledge_bases/esp/events/event_taxonomy.yaml"
    assert os.path.exists(tax_path), f"Taxonomy file missing: {tax_path}"

    with open(tax_path, "r", encoding="utf-8") as f:
        tax = yaml.safe_load(f)

    assert "event_types" in tax
    assert "ESP_TRIPPED" in tax["event_types"]
    assert "FAILURE_RISK_INCREASED" in tax["event_types"]
    assert tax["event_types"]["ESP_TRIPPED"]["target_objective_id"] == "OP03_FAULT_DIAGNOSIS"
    assert tax["event_types"]["FAILURE_RISK_INCREASED"]["target_objective_id"] == "OP05_EARLY_WARNING"
