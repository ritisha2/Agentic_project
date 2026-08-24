# Skill: Telemetry Adapter

## Purpose
Translates raw, domain-specific telemetry inputs into canonical `TelemetryMetric` objects using `mapping_config.json`.

## Inputs
- `asset_id`: String identifier for target equipment.
- `time_window`: Optional timeframe for telemetry lookup.

## Outputs
- List of canonical `TelemetryMetric` models with parameter names, values, units, metric types, and health statuses.

## Logic
1. Load telemetry source (CSV, stream, or database).
2. Filter latest record for target `asset_id`.
3. Map raw parameter names (e.g. `motor_temperature`) to canonical fields (e.g. `primary_thermal_metric`).
4. Validate values against range boundaries.
