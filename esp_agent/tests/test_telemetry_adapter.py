import pytest
import os
from src.adapters.telemetry import TelemetryAdapter
from src.schemas.mapping import MappingConfig, FieldMapping


def test_telemetry_adapter_mapping():
    mapping_path = "knowledge_bases/esp/mapping_config.json"
    telemetry_path = "knowledge_bases/esp/telemetry/esp_telemetry.csv"

    adapter = TelemetryAdapter.from_config_file(
        mapping_config_path=mapping_path,
        telemetry_csv_path=telemetry_path
    )

    metrics = adapter.load_latest_telemetry(asset_id="ESP-Well-001")
    assert len(metrics) > 0

    metric_names = [m.parameter_name for m in metrics]
    assert "primary_thermal_metric" in metric_names
    assert "vibration_metric" in metric_names
    assert "primary_intake_pressure" in metric_names

    # Check metric object fields
    thermal = next(m for m in metrics if m.parameter_name == "primary_thermal_metric")
    assert thermal.metric_type == "thermal"
    assert thermal.unit == "°C"


def test_telemetry_adapter_file_not_found():
    adapter = TelemetryAdapter.from_config_file("knowledge_bases/esp/mapping_config.json")
    with pytest.raises(FileNotFoundError):
        adapter.load_latest_telemetry(asset_id="ESP-Well-001", csv_path="invalid/path.csv")
