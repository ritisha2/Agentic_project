# Mock API Backup — Retired Telemetry Mock & VFD Bridge

**Status:** ARCHIVED — not imported by any live code path. Isolated on 2026-09-01.

## Why this was retired

The live telemetry pipeline no longer needs a synthetic mock server. The
actual flow is now:

```
Real MQTT broker (192.168.1.155:1883)
    -> cced_esp/backend/mqtt_collector.py       (paho-mqtt subscriber)
    -> cced_esp/backend/transformer.py           (existing DB-schema mapping, UNCHANGED)
                                                   + extract_vfd_signals()  (NEW, additive)
    -> cced_esp/backend/services/vfd_diagnostic_service.py
    -> ESP_APM_models.WellDiagnosticEngine.evaluate_live_telemetry()
    -> cced_esp/data/logs/vfd_diagnostics.jsonl  (agent-readable log)
       + console "Operator Diagnostic Intelligence Card" print
```

DB writes to `opg_well_telemetry` (labelled.db / unlabelled.db) continue
exactly as before — this change is purely additive on top of the existing
MQTT ingestion path. No 14-VFD-parameter mock server is required anywhere in
this flow; `extract_vfd_signals()` resolves whatever real fields the actual
MQTT payload carries (old snake_case, legacy `R_*` SCADA tags, or literal VFD
names) and lets `WellDiagnosticEngine`'s own calibrated-median fill cover
anything the payload doesn't provide.

## What's archived here

| File | Original location | Purpose (when live) |
|---|---|---|
| `telemetry_mock_server.py` | `esp_agent/src/api/` | Standalone FastAPI mock (:8081) simulating 14-VFD-signal telemetry ingestion/history endpoints. |
| `telemetry_mock_schemas.py` | `esp_agent/src/api/` | Pydantic schemas + `VFD_CANONICAL_UNITS` map backing the mock server. |
| `test_telemetry_mock_api.py` | `esp_agent/tests/` | Test suite exercising the mock server's endpoints. |
| `vfd_model_adapter.py` | `esp_agent/src/adapters/` | Dormant bridge from the mock's output shape to `ESP_APM_models.WellDiagnosticEngine`. Confirmed to have zero live callers before archival — `run_vfd_diagnostic()` was defined but never invoked anywhere in the active codebase. |

Internal cross-references between these four files (`telemetry_mock_server.py`
importing `telemetry_mock_schemas`, `test_telemetry_mock_api.py` importing
`telemetry_mock_server`) were updated to flat local imports so this folder
remains internally coherent and re-runnable in isolation if ever needed
(e.g. `cd mock_api_backup && uvicorn telemetry_mock_server:app --port 8081`).
No other files in the workspace import any of these four modules — confirmed
via full-repo grep before archival.

## Restoring (if ever needed)

1. Move the four files back to their "Original location" column above.
2. Revert the two import-path edits noted above back to `src.api.*` / `src.adapters.*`.
3. Re-add `esp_agent/tests/test_telemetry_mock_api.py` to your test discovery if excluded.
