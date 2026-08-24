# Skill: Rule Adapter

## Purpose
Evaluates deterministic threshold rules against canonical telemetry metrics to identify parameter violations.

## Inputs
- List of canonical `TelemetryMetric` models.

## Outputs
- List of rule evaluation objects containing `rule_id`, `metric_name`, `observed_value`, `threshold`, and `severity`.
