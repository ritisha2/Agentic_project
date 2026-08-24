from src.adapters.rules import RuleAdapter
from src.schemas.canonical import TelemetryMetric


def test_rule_adapter_evaluation():
    rules_path = "knowledge_bases/esp/rules/diagnostic_rules.json"
    adapter = RuleAdapter.from_file(rules_path)

    # Test metrics exceeding thermal limit
    metrics = [
        TelemetryMetric(
            parameter_name="primary_thermal_metric",
            metric_type="thermal",
            current_value=140.0,
            unit="°C",
            status="warning",
            timestamp="2026-01-01T00:00:00"
        ),
        TelemetryMetric(
            parameter_name="primary_intake_pressure",
            metric_type="pressure",
            current_value=300.0,
            unit="psi",
            status="normal",
            timestamp="2026-01-01T00:00:00"
        ),
    ]

    evaluations = adapter.evaluate_rules(metrics)
    assert len(evaluations) > 0
    rule_ids = [e["rule_id"] for e in evaluations]
    assert "RULE_TEMP_WARN" in rule_ids
