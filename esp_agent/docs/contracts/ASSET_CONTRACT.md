# Sprint 2.1 — Advait Asset Registry API Contract

> **Phase 2 Deliverable:** Sprint 2.1 Asset Contract Specification  
> **Source Platform:** Advait Asset Registry / Client Platform  
> **Date:** 2026-08-25  

---

## 1. Overview & Service Scope

The **Asset Context Service** provides normalized identity, structural configuration, OEM component ratings, and operational limits for ESP installations. It acts as a projection cache over the Advait Platform.

---

## 2. API Endpoints

### 2.1 List All Assets
- **Endpoint:** `GET /api/v1/assets`
- **Query Parameters:** `status` (optional: `ACTIVE`, `SHUT_IN`, `TRIPPED`), `limit` (default: 50)
- **Response `200 OK`:**
```json
{
  "total_count": 1,
  "assets": [
    {
      "asset_id": "ESP-Well-001",
      "well_id": "WELL-001",
      "asset_type": "ESP",
      "status": "ACTIVE",
      "source_system": "ADVAIT",
      "pump_model": "Weatherford DN1750",
      "last_sync": "2026-08-25T12:00:00Z"
    }
  ]
}
```

### 2.2 Get Detailed Asset Context
- **Endpoint:** `GET /api/v1/assets/{asset_id}`
- **Response `200 OK`:**
```json
{
  "asset_id": "ESP-Well-001",
  "well_id": "WELL-001",
  "asset_type": "ESP",
  "status": "ACTIVE",
  "source_system": "ADVAIT",
  "installation_depth_ft": 8500.0,
  "pump_model": "Weatherford DN1750",
  "motor_rating_hp": 250.0,
  "nameplate_current_amps": 65.0,
  "be_point_bpd": 1750.0,
  "subsystems": ["Motor", "Pump", "Seal", "Intake", "VSD"],
  "last_sync": "2026-08-25T12:00:00Z"
}
```

---

## 3. Failure & Retry Policy

- **Timeout:** 2000 ms
- **Retry Strategy:** 3 retries with exponential backoff (`100ms`, `300ms`, `900ms`).
- **Fallback Behavior:** If Advait API is unreachable, `AssetService` returns the cached PostgreSQL/SQLite asset projection and sets `source_system: "ADVAIT_CACHE"`.
