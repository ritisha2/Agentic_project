# ADVAIT Asset API Mock / Ingestion Service

Mock/adapter boundary for the ESP Agent. It mirrors the canonical Asset Context schema and accepts simulator telemetry.

## Run
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

Open http://localhost:8000/docs

## Key endpoints
GET  /api/v1/assets
GET  /api/v1/assets/{asset_id}/context
GET  /api/v1/assets/{asset_id}/tags
GET  /api/v1/assets/{asset_id}/fault-catalog
POST /api/v1/telemetry
GET  /api/v1/assets/{asset_id}/telemetry/latest
GET  /api/v1/assets/{asset_id}/telemetry/history

## Example telemetry
{
  "asset_id":"FS-031",
  "timestamp":"2026-08-26T04:54:33.739Z",
  "scenario":"normal",
  "state":"running",
  "values":{
    "liquid_rate_bpd":735.7,
    "intake_pressure_psi":236.5,
    "discharge_pressure_psi":1883.7,
    "frequency_hz":46.06,
    "motor_current_a":18.86,
    "motor_voltage_v":1006.3,
    "motor_temperature_c":79.67,
    "vibration_rms_g":0.1758
  },
  "voltage_imbalance_pct":0.60,
  "current_imbalance_pct":1.00
}

This is a mock. Replace the seed repository with an Advait adapter later without changing the Agent-facing context contract.
