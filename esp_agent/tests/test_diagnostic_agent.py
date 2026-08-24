import os
import json
import pytest
from src.agent.runtime import DiagnosticAgentRuntime
from src.schemas.canonical import DiagnosticResult


KB_PATH = "knowledge_bases/esp"


def test_1_normal_operation():
    runtime = DiagnosticAgentRuntime(kb_path=KB_PATH)
    res = runtime.run_diagnosis(
        user_query="ESP-Well-001 is operating normally, any issues?",
        asset_id="ESP-Well-001"
    )
    assert res.confidence_score >= 0.8
    assert res.severity_level == "normal"
    assert "no issues" in res.identified_fault.lower() or "normal" in res.identified_fault.lower()


def test_2_motor_overheating():
    runtime = DiagnosticAgentRuntime(kb_path=KB_PATH)
    res = runtime.run_diagnosis(
        user_query="ESP-Well-001 motor temperature is 140°C, what should I do?",
        asset_id="ESP-Well-001"
    )
    assert res.confidence_score >= 0.75
    assert res.severity_level == "warning"
    assert "overheating" in res.identified_fault.lower() or "thermal" in res.identified_fault.lower()
    assert "reduce flow rate" in res.recommended_action.lower() or "pip" in res.recommended_action.lower()


def test_3_excessive_vibration():
    runtime = DiagnosticAgentRuntime(kb_path=KB_PATH)
    res = runtime.run_diagnosis(
        user_query="ESP-Well-001 has high vibration (3.5 g radial)",
        asset_id="ESP-Well-001"
    )
    assert res.confidence_score >= 0.75
    assert res.severity_level == "warning"
    assert "bearing" in res.identified_fault.lower() or "vibration" in res.identified_fault.lower()
    assert "bearing" in res.recommended_action.lower() or "alignment" in res.recommended_action.lower()


def test_4_low_pip():
    runtime = DiagnosticAgentRuntime(kb_path=KB_PATH)
    res = runtime.run_diagnosis(
        user_query="ESP-Well-001 PIP dropped to 120 psi",
        asset_id="ESP-Well-001"
    )
    assert res.confidence_score >= 0.75
    assert res.severity_level == "warning"
    assert "gas lock" in res.identified_fault.lower() or "pressure" in res.identified_fault.lower()
    assert "flow rate" in res.recommended_action.lower() or "vsd" in res.recommended_action.lower()


def test_5_missing_capability():
    """Agent handles missing graph or RAG gracefully when capability flags are disabled in manifest."""
    runtime = DiagnosticAgentRuntime(kb_path=KB_PATH)
    # Simulate disabled RAG and Graph capabilities
    if runtime.manifest:
        runtime.manifest.supports_graph = False
        runtime.manifest.supports_rag = False
    runtime._init_adapters()

    res = runtime.run_diagnosis(
        user_query="ESP-Well-001 motor temperature is 140°C",
        asset_id="ESP-Well-001"
    )
    # Should still diagnose based on telemetry & rules without crashing
    assert "overheating" in res.identified_fault.lower() or "thermal" in res.identified_fault.lower()


def test_6_different_field_names(tmp_path):
    """Agent works when raw field names are completely changed, requiring only a mapping_config change."""
    # Create temporary KB with renamed field names (e.g., motor_temp -> engine_heat_val)
    test_kb_dir = tmp_path / "renamed_esp_kb"
    test_kb_dir.mkdir()

    # Copy metadata
    with open(os.path.join(KB_PATH, "metadata.json"), "r") as f:
        meta = json.load(f)
    meta["domain_name"] = "Renamed ESP Domain"
    with open(test_kb_dir / "metadata.json", "w") as f:
        json.dump(meta, f)

    # Renamed mapping
    renamed_mapping = {
        "domain_id": "ESP_RENAMED",
        "field_mappings": [
            {
                "source_field": "engine_heat_val",
                "canonical_field": "primary_thermal_metric",
                "data_type": "float",
                "unit": "°C",
                "valid_range": [80.0, 130.0],
                "is_required": True
            }
        ]
    }
    with open(test_kb_dir / "mapping_config.json", "w") as f:
        json.dump(renamed_mapping, f)

    # Telemetry directory with renamed column
    tel_dir = test_kb_dir / "telemetry"
    tel_dir.mkdir()
    tel_csv = tel_dir / "esp_telemetry.csv"
    tel_csv.write_text("timestamp,asset_id,engine_heat_val\n2026-01-01T00:00:00,ESP-Well-001,142.0\n")

    # Rules
    rules_dir = test_kb_dir / "rules"
    rules_dir.mkdir()
    with open(os.path.join(KB_PATH, "rules", "diagnostic_rules.json"), "r") as f:
        rules_data = json.load(f)
    with open(rules_dir / "diagnostic_rules.json", "w") as f:
        json.dump(rules_data, f)

    runtime = DiagnosticAgentRuntime(kb_path=str(test_kb_dir))
    res = runtime.run_diagnosis(
        user_query="Engine heat high",
        asset_id="ESP-Well-001"
    )
    assert "overheating" in res.identified_fault.lower() or "thermal" in res.identified_fault.lower()


def test_7_unknown_asset():
    runtime = DiagnosticAgentRuntime(kb_path=KB_PATH)
    res = runtime.run_diagnosis(
        user_query="Check asset status",
        asset_id="NON-EXISTENT-PUMP-999"
    )
    assert "asset not found" in res.identified_fault.lower()
    assert res.confidence_score == 0.0


def test_8_missing_telemetry(tmp_path):
    # Temporary KB with no telemetry CSV
    test_kb_dir = tmp_path / "empty_telemetry_kb"
    test_kb_dir.mkdir()

    with open(os.path.join(KB_PATH, "metadata.json"), "r") as f:
        meta = json.load(f)
    with open(test_kb_dir / "metadata.json", "w") as f:
        json.dump(meta, f)

    with open(os.path.join(KB_PATH, "mapping_config.json"), "r") as f:
        mapping = json.load(f)
    with open(test_kb_dir / "mapping_config.json", "w") as f:
        json.dump(mapping, f)

    runtime = DiagnosticAgentRuntime(kb_path=str(test_kb_dir))
    res = runtime.run_diagnosis(
        user_query="Diagnose pump state",
        asset_id="ESP-Well-001"
    )
    assert "insufficient telemetry data" in res.identified_fault.lower()
