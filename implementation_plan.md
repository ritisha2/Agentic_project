# Complete ESP-APM ↔ esp_agent Integration Plan

**Goal**: Fully connect the ESP-APM platform (cced_esp frontend + backend) to the esp_agent LangGraph Supervisor backend so Agent Jane queries use **real live telemetry, real ML assessments, and real engineering data** — not mock hardcoded values.

---

## Current State After Phase 1 (Already Done)

| Layer | Status | What We Built |
|---|---|---|
| **Frontend → Agent Gateway** | ✅ Done | Vite proxy `/api/agent` → `:8090`, `agentApi.js` NDJSON stream reader |
| **Agent Dock UI** | ✅ Done | Minimal, SCADA-themed `AgentFloatingDock.jsx` |
| **Agent Gateway Server** | ✅ Done | `run_agent_server.py` on `:8090` |

## What's Still Missing (The Heavy Lifting)

The esp_agent's internal services currently use **mock/fallback data**:

| esp_agent Service | Current Data Source | Problem |
|---|---|---|
| `TelemetryService.get_latest()` | Hardcoded fallback values (`flow=1450`, `pip=350`, etc.) | Not using real MQTT telemetry from cced_esp |
| `AssetContextService` | Local JSON seed file (`asset_context_initial_seed_v2_rich.json`) | Doesn't see the 26-asset live fleet from cced_esp |
| `EngineeringService` | Pure physics formulas (correct) but fed mock inputs | Needs real PDP/PIP/flow from live telemetry |
| Supervisor `load_minimum_context_node` | Hardcoded `tdh_ft=4042.5`, `confidence=0.88` | Should pull real ML assessment from cced_esp pipeline |
| BFF `stream` endpoint | Hardcoded advisory text and chart data | Should use live Supervisor output (already wired) |

---

## Architecture: LiveDataBridge Pattern

```
┌───────────────────────────────────────────────────────────┐
│  esp_agent Gateway (:8090)                                │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  LangGraph Supervisor Graph                         │ │
│  │  ┌──────────────┐  ┌──────────────┐                 │ │
│  │  │ resolve_asset│→ │ data_quality │→ ...            │ │
│  │  └──────┬───────┘  └──────┬───────┘                 │ │
│  │         │                 │                          │ │
│  │         ▼                 ▼                          │ │
│  │  ┌─────────────────────────────────────────────┐    │ │
│  │  │         LiveDataBridge (NEW)                 │    │ │
│  │  │  HTTP client calling cced_esp :8000 APIs    │    │ │
│  │  │                                              │    │ │
│  │  │  GET /api/esp/assets → real 26-asset fleet   │    │ │
│  │  │  GET /api/telemetry?asset_id=X → real data   │    │ │
│  │  │  GET /api/esp/assets/{id}/latest-assessment  │    │ │
│  │  │  GET /api/analytics/timeseries?asset_id=X    │    │ │
│  │  └─────────────────────────────────────────────┘    │ │
│  └──────────────────────────────────────────────────────┘ │
│                         │                                  │
│                    HTTP calls                              │
│                         ▼                                  │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  cced_esp Backend (:8000)                            │ │
│  │  MQTT Collector → SQLite DB → ML Pipeline            │ │
│  │  26 Live Assets · Fault Classifier · Health Index    │ │
│  └──────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **No folder moves. No code duplication.** We add a single `LiveDataBridge` adapter in esp_agent that makes HTTP calls to the already-running cced_esp backend on `:8000` to pull real data.

---

## Proposed Changes

### Component 1: LiveDataBridge Adapter

#### [NEW] [live_data_bridge.py](file:///x:/TAS/Agentic_project/esp_agent/src/adapters/live_data_bridge.py)

A lightweight HTTP client adapter that calls the cced_esp backend REST APIs to fetch real data:

```python
class LiveDataBridge:
    """HTTP bridge to cced_esp backend (:8000) for live telemetry, ML assessments, and fleet data."""
    
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
    
    def get_live_telemetry(self, asset_id: str) -> dict:
        """GET /api/telemetry?asset_id={id}&limit=1 → latest real sensor reading"""
    
    def get_fleet_assets(self) -> list[dict]:
        """GET /api/esp/assets → all 26 live assets with health index"""
    
    def get_latest_assessment(self, asset_id: str) -> dict:
        """GET /api/esp/assets/{id}/latest-assessment → ML fault classification + anomaly score"""
    
    def get_timeseries(self, asset_id: str, limit=60) -> list[dict]:
        """GET /api/analytics/timeseries?asset_id={id} → chart data for generative UI"""
    
    def is_available(self) -> bool:
        """GET /api/status → True if cced_esp backend is reachable"""
```

**Key design**: Uses `httpx` (already in esp_agent deps) with a 3-second timeout. Falls back gracefully to existing mock data if cced_esp backend is offline.

---

### Component 2: Inject Live Data into Supervisor Graph

#### [MODIFY] [graph.py](file:///x:/TAS/Agentic_project/esp_agent/src/agent/supervisor/graph.py)

Two nodes need live data injection:

**Node 3 — `data_quality_gate_node`** (line 90-126):
- Currently uses hardcoded `telemetry_data = {"motor_temperature": 135.0, ...}`
- **Change**: Call `LiveDataBridge.get_live_telemetry(asset_id)` to pull real sensor readings from cced_esp. If bridge is offline, fall back to existing mock values.

**Node 4 — `load_minimum_context_node`** (line 128-142):
- Currently uses hardcoded `ctx["engineering"] = {"tdh_ft": 4042.5, ...}` and `ctx["models"] = {"predicted_fault": "Intake Pressure Drawdown", "confidence": 0.88}`
- **Change**: Call `LiveDataBridge.get_latest_assessment(asset_id)` to get real ML fault class, confidence, anomaly score, and health index. Compute real TDH from live PDP/PIP values.

---

### Component 3: BFF Streaming with Live Data

#### [MODIFY] [bff_routes.py](file:///x:/TAS/Agentic_project/esp_agent/src/api/rest/bff_routes.py)

The `/api/ui/agent/stream` endpoint currently generates hardcoded chart data (lines 202-237). 

**Change**: After the Supervisor advisory is generated, call `LiveDataBridge.get_timeseries(asset_id)` to build the Plotly chart from **real historical telemetry** instead of the hardcoded `[1750, 1720, 1680, ...]` arrays.

The advisory text streaming (lines 174-199) is already dynamic since it reads from the Supervisor's real advisory output — this part stays as-is.

---

### Component 4: BFF Workspace Endpoint with Live Data

#### [MODIFY] [bff_routes.py](file:///x:/TAS/Agentic_project/esp_agent/src/api/rest/bff_routes.py)

The `GET /api/ui/assets/{asset_id}/workspace` endpoint (line 40-78) currently returns mock engineering values.

**Change**: Call `LiveDataBridge.get_live_telemetry()` and `LiveDataBridge.get_latest_assessment()` to populate the workspace payload with real telemetry snapshot, real ML predictions, and real engineering calculations.

---

### Component 5: Environment Configuration

#### [MODIFY] [.env.example](file:///x:/TAS/Agentic_project/esp_agent/.env.example)

Add the cced_esp backend URL so the bridge knows where to connect:

```env
# LiveDataBridge — cced_esp backend connection
CCED_ESP_BACKEND_URL=http://127.0.0.1:8000
```

---

## File Summary

| Action | File | Purpose |
|---|---|---|
| **NEW** | `esp_agent/src/adapters/live_data_bridge.py` | HTTP client bridge to cced_esp backend APIs |
| **MODIFY** | `esp_agent/src/agent/supervisor/graph.py` | Inject live telemetry + ML data into graph nodes 3 & 4 |
| **MODIFY** | `esp_agent/src/api/rest/bff_routes.py` | Use live timeseries for charts, live telemetry for workspace |
| **MODIFY** | `esp_agent/.env.example` | Add `CCED_ESP_BACKEND_URL` config |

---

## Open Questions

> [!IMPORTANT]
> **Q1: Backend Availability Behavior** — When the cced_esp backend (:8000) is offline, should Agent Jane:
> - **(A)** Fall back silently to mock data (current behavior, seamless but less transparent)
> - **(B)** Show a warning badge in the response like `⚠️ Using offline mock data — live telemetry unavailable`

> [!IMPORTANT]
> **Q2: Asset ID Mapping** — The cced_esp fleet uses IDs like `FS-010`, `FS-031`, `FSWS-001-A`. The esp_agent's local seed file also has its own asset IDs. Should the LiveDataBridge:
> - **(A)** Always prefer cced_esp fleet data when available (recommended)
> - **(B)** Merge both sources

---

## Verification Plan

### Automated Tests
```bash
# 1. Verify cced_esp backend is running and serving data
curl http://127.0.0.1:8000/api/status

# 2. Verify esp_agent gateway is running
curl http://127.0.0.1:8090/health

# 3. Run Agent query and verify real telemetry values in response
curl -N -X POST http://127.0.0.1:8090/api/ui/agent/stream \
  -H "Content-Type: application/json" \
  -d '{"user_query": "Diagnose FS-031 production decline", "asset_id": "FS-031"}'
# Verify: text_delta events contain real sensor values (not hardcoded 1450 BPD / 350 PSI)
# Verify: generative_ui chart contains real timeseries data points
```

### Manual Verification
1. Start cced_esp backend (:8000), esp_agent gateway (:8090), and frontend (:3000)
2. Open ESP-APM dashboard and observe live telemetry for an asset (e.g., `FS-031`)
3. Click Agent Jane → ask "Diagnose this well"
4. Verify the advisory response references the **same real-time values** visible on the dashboard (not generic mock data)
5. Verify the Plotly chart on the canvas shows **real historical trend data** matching the dashboard trends
