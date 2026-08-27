# Sprint 2.2 — Telemetry Service API Contract

> **Phase 2 Deliverable:** Sprint 2.2 Telemetry Contract Specification  
> **Source Platform:** Simulator / OT SCADA Platform  
> **Date:** 2026-08-25  

---

## 1. Overview & Service Scope

The **Telemetry Service** normalizes live and historical sensor signals into canonical `TelemetryMetric` payloads. It enforces unit standardization (`°C`, `psi`, `bpd`, `Hz`, `amps`) and evaluates sensor Data Quality (`GOOD`, `DEGRADED`, `STALE`).

---

## 2. API Endpoints

### 2.1 Get Live Telemetry Snapshot
- **Endpoint:** `GET /api/v1/assets/{asset_id}/telemetry/live`
- **Response `200 OK`:**
```json
{
  "asset_id": "ESP-Well-001",
  "timestamp": "2026-08-25T12:00:00Z",
  "data_quality_summary": "GOOD",
  "metrics": {
    "motor_temperature": {
      "tag": "motor_temperature",
      "value": 135.0,
      "unit": "°C",
      "timestamp": "2026-08-25T12:00:00Z",
      "quality": "GOOD"
    },
    "discharge_pressure": {
      "tag": "discharge_pressure",
      "value": 2100.0,
      "unit": "psi",
      "timestamp": "2026-08-25T12:00:00Z",
      "quality": "GOOD"
    },
    "intake_pressure": {
      "tag": "intake_pressure",
      "value": 350.0,
      "unit": "psi",
      "timestamp": "2026-08-25T12:00:00Z",
      "quality": "GOOD"
    },
    "flow_rate": {
      "tag": "flow_rate",
      "value": 1450.0,
      "unit": "bpd",
      "timestamp": "2026-08-25T12:00:00Z",
      "quality": "GOOD"
    },
    "current": {
      "tag": "current",
      "value": 62.0,
      "unit": "amps",
      "timestamp": "2026-08-25T12:00:00Z",
      "quality": "GOOD"
    }
  }
}
```

### 2.2 Get Historical Telemetry Window
- **Endpoint:** `GET /api/v1/assets/{asset_id}/telemetry/history`
- **Query Parameters:** `start_time`, `end_time`, `resolution` (e.g. `1m`, `15m`, `1h`), `signals` (comma-separated tags)
- **Response `200 OK`:** Returns array of historical signal snapshots.

---

## 3. Failure & Quality Policy

- **Timeout:** 3000 ms
- **Stale Telemetry Threshold:** Telemetry older than 300 seconds is marked `quality: "STALE"` and `data_quality_summary: "STALE"`.
- **Fallback Behavior:** If live stream fails, falls back to recent CSV snapshot and explicitly discloses missing/stale telemetry to the Agent.
