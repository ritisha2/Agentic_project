# ⚡ ESP Agentic APM Platform

> **Autonomous AI Agentic Engineering & Diagnostic Management System for Electric Submersible Pumps (ESP)**

Built with a LangGraph Supervisor multi-agent backbone, deterministic physics engines, dual-tier ML inference, and a Next.js Generative UI workspace — purpose-built for oil & gas ESP fleet monitoring, diagnosis, and engineering analysis.

---

## 📋 Table of Contents

1. [System Architecture](#system-architecture)
2. [Repository Structure](#repository-structure)
3. [Microservice Network & Port Map](#microservice-network--port-map)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Running the Application](#running-the-application)
8. [Health Check](#health-check)
9. [Running Tests](#running-tests)
10. [Offline / LLM-Free Mode](#offline--llm-free-mode)
11. [API Reference](#api-reference)
12. [Generative UI Workspace](#generative-ui-workspace)
13. [Agent Architecture](#agent-architecture)
14. [Engineering Calculation Engine](#engineering-calculation-engine)
15. [ML Model Integration](#ml-model-integration)
16. [Troubleshooting](#troubleshooting)
17. [Documentation Index](#documentation-index)

---

## System Architecture

```
 +----------------------------------------------------------+
 |           NEXT.JS 16 GENERATIVE UI WORKSPACE             |
 |   Agent Jane Dialog . Plotly Charts . Generative Blocks  |
 |                  http://localhost:3000                    |
 +---------------------------+------------------------------+
                             | NDJSON Streaming (SSE) / REST
                             v
 +----------------------------------------------------------+
 |         FASTAPI BACKEND-FOR-FRONTEND (BFF) GATEWAY       |
 |            LangGraph Supervisor . Policy Gate            |
 |                  http://localhost:8000                    |
 +----------+------------------+----------------------------+
            |                  |                  |
            v                  v                  v
 +------------------+  +------------------+  +------------------+
 | ESP Telemetry    |  | ESP ML Model API |  | ESP Engineering  |
 | Mock API   :8081 |  | Inference  :8082 |  | Service    :8083 |
 +------------------+  +------------------+  +------------------+

 +------------------------------------------------------------------+
 |              LANGGRAPH SUPERVISOR MULTI-AGENT                    |
 |  ReliabilitySpecialist | EngineeringSpecialist                   |
 |  WellPerformanceSpecialist | DigitalTwinSpecialist               |
 |  MaintenanceSpecialist | KnowledgeSpecialist                     |
 +------------------------------------------------------------------+
```

---

## Repository Structure

```
.
├── README.md                              <- You are here
│
├── docs/                                  <- Master Documentation Hub
│   ├── architecture/                      <- Architecture design specs (.docx)
│   │   ├── ESP_APM_Engineering_Service_Architecture_Granular_Design.docx
│   │   ├── ESP_APM_ML_Model_Integration_and_Consumption_Design.docx
│   │   ├── ESP_APM_PHASE_8_Evidence_Pack_Agent_Context_Implementation_Design.docx
│   │   ├── ESP_APM_PHASE_9_FRONTEND_BACKEND_PRODUCT_INTEGRATION_ARCHITECTURE.docx
│   │   ├── ESP_APM_Telemetry_Mock_API_Specification.docx
│   │   └── ESP_APM_Telemetry_Service_Consumption_Architecture.docx
│   ├── specifications/                    <- Technical contracts & dependencies (.md)
│   │   ├── ESP_Agentic_ML_Team_Dependencies_and_API_PreRequisites.md
│   │   ├── ESP_Engineering_Research_Package.md
│   │   └── dependency_detail.md
│   └── engineering_registry/             <- Immutable formula & OEM registries
│
├── esp_agent/                             <- Primary Application Root
│   ├── .env.example                       <- Environment variable template
│   ├── docker-compose.yml                 <- Infrastructure (Qdrant, Neo4j, Postgres, Redis)
│   ├── pyproject.toml                     <- Python package config (Python >= 3.10)
│   ├── requirements.txt                   <- Python dependencies
│   ├── langgraph.json                     <- LangGraph runtime configuration
│   │
│   ├── src/                               <- Core Python Application
│   │   ├── main.py                        <- FastAPI BFF entrypoint (:8000)
│   │   ├── adapters/                      <- External system adapters
│   │   │   ├── telemetry_adapter.py       <- Telemetry API client (:8081)
│   │   │   ├── ml_model_adapter.py        <- ML Model API client (:8082)
│   │   │   ├── rag_adapter.py             <- Qdrant vector store adapter
│   │   │   └── rule_adapter.py            <- Rule-based advisory engine
│   │   ├── agent/                         <- LangGraph Agent Runtime
│   │   │   ├── runtime.py                 <- Supervisor graph orchestration
│   │   │   ├── intent_router.py           <- Query intent classification
│   │   │   ├── objective_router.py        <- Objective routing & dispatch
│   │   │   ├── objective_registry.py      <- Objective catalogue
│   │   │   ├── data_quality_gate.py       <- Input quality validation gate
│   │   │   ├── state.py                   <- Agent state schemas
│   │   │   ├── specialists/               <- Specialist LangGraph subgraphs
│   │   │   │   ├── reliability.py         <- ReliabilitySpecialist (ML + rules)
│   │   │   │   ├── engineering.py         <- EngineeringSpecialist (calc engine)
│   │   │   │   ├── well_performance.py    <- WellPerformanceSpecialist
│   │   │   │   ├── digital_twin.py        <- DigitalTwinSpecialist
│   │   │   │   ├── maintenance.py         <- MaintenanceSpecialist
│   │   │   │   └── knowledge.py           <- KnowledgeSpecialist (RAG)
│   │   │   ├── supervisor/                <- Supervisor node & routing logic
│   │   │   └── workflows/                 <- Multi-step workflow graphs
│   │   ├── api/                           <- FastAPI Servers
│   │   │   ├── fastapi_app.py             <- Main app factory
│   │   │   ├── telemetry_mock_server.py   <- Standalone Telemetry API (:8081)
│   │   │   ├── ml_model_mock_server.py    <- Standalone ML Model API (:8082)
│   │   │   ├── engineering_service_server.py <- Standalone Engineering API (:8083)
│   │   │   ├── cli.py                     <- Command-line interface
│   │   │   ├── mcp/                       <- MCP (Model Context Protocol) server
│   │   │   └── rest/
│   │   │       └── bff_routes.py          <- /api/ui/* endpoints + NDJSON streaming
│   │   ├── events/                        <- Event stream models & persistence
│   │   ├── llm/
│   │   │   └── gateway.py                 <- llama.cpp local LLM client
│   │   ├── policy/                        <- Safety gate & guardrails
│   │   ├── schemas/
│   │   │   └── engineering_contracts.py   <- Engineering calculation schemas
│   │   └── services/
│   │       ├── asset_context_service.py   <- Asset context & metadata
│   │       ├── engineering/               <- Physics calculation engine
│   │       │   ├── engine.py              <- Deterministic calc engine (A1-G3)
│   │       │   ├── oem_repository.py      <- OEM pump curve master data
│   │       │   └── calculation_registry.py <- Formula catalogue loader
│   │       ├── retrieval_service.py       <- RAG knowledge retrieval
│   │       ├── telemetry_service.py       <- Telemetry data service
│   │       └── xai_service.py             <- Explainable AI evidence service
│   │
│   ├── tests/                             <- Pytest Integration Test Suite (48 files)
│   │   ├── test_engineering_service.py    <- 9 engineering calc tests
│   │   ├── test_telemetry_mock_api.py     <- Telemetry API tests
│   │   ├── test_ml_model_integration.py   <- ML adapter tests
│   │   ├── test_phase10_llm_layer.py      <- LLM gateway tests
│   │   └── test_phase*.py                 <- Phased integration tests (phases 1-10)
│   │
│   └── ui/                                <- Next.js 16 Frontend
│       ├── package.json
│       ├── src/
│       │   ├── app/workspace/[assetId]/   <- Dynamic workspace page
│       │   ├── components/
│       │   │   └── dialog/
│       │   │       ├── AgentDialog.tsx    <- Floating, resizable dialog
│       │   │       └── GenerativeUIBlocks.tsx <- Markdown, Plotly, action cards
│       │   └── lib/api.ts                 <- API client + NDJSON stream reader
│       └── next.config.ts
│
├── data/                                  <- Sample datasets & telemetry fixtures
├── esp-knowledge/                         <- Knowledge base documents
├── models/                               <- LLM model files (local llama.cpp)
├── tools/                                <- Helper tooling & scripts
└── bin/                                  <- Binary utilities
```

---

## Microservice Network & Port Map

| Port | Service | Description | Health Check |
|------|---------|-------------|--------------|
| **3000** | Next.js UI Workspace | Generative UI, Agent Jane dialog, Plotly charts | `GET http://localhost:3000/workspace/FS-031` |
| **8000** | FastAPI BFF Gateway | LangGraph supervisor, NDJSON streaming, REST API | `GET http://localhost:8000/health` |
| **8081** | ESP Telemetry API | Canonical telemetry snapshots, asset listing | `GET http://localhost:8081/health` |
| **8082** | ESP ML Model API | Fault classification, 24h risk prediction | `GET http://localhost:8082/api/v1/models/health` |
| **8083** | ESP Engineering API | Deterministic calc engine (A1-G3), OEM curves | `GET http://localhost:8083/health` |

**Infrastructure Services (Docker — Optional):**

| Port | Service | Purpose |
|------|---------|---------|
| **6333** | Qdrant | Vector database for RAG knowledge retrieval |
| **7474** | Neo4j HTTP | Graph database for asset relationships |
| **7687** | Neo4j Bolt | Neo4j Bolt protocol |
| **5432** | PostgreSQL | Relational event store |
| **6379** | Redis | Event stream broker |
| **8080** | llama.cpp server | Local LLM inference (CPU, no GPU required) |

---

## Prerequisites

### Required

| Dependency | Version | Notes |
|------------|---------|-------|
| **Python** | >= 3.10 | Backend, agent runtime, microservices |
| **Node.js** | >= 18.x | Next.js frontend |
| **npm** | >= 9.x | Node package manager |

### Optional (Full Mode with LLM + Vector DB)

| Dependency | Version | Notes |
|------------|---------|-------|
| **Docker Desktop** | latest | For Qdrant, Neo4j, PostgreSQL, Redis |
| **llama.cpp** | latest | Local LLM server (CPU inference, no GPU needed) |

> **Note**: The platform runs fully in **Offline Mode** without Docker or llama.cpp. See [Offline / LLM-Free Mode](#offline--llm-free-mode).

---

## Installation

### Step 1 — Python Backend Setup

```bash
# Navigate into the backend application root
cd esp_agent

# Create and activate a virtual environment
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install the package in editable mode (required for python -m src.* imports)
pip install -e .
```

### Step 2 — Node.js Frontend Setup

The application's frontend is `cced_esp/frontend-react` — a standalone React (Vite) SCADA/telemetry dashboard. `esp_agent` has no frontend of its own; it is a backend-only agent/API service consumed via REST (`:8090`) or CLI tools (`query_historian.py`, etc.).

```bash
# From the repository root
cd cced_esp/frontend-react

# Install all Node dependencies
npm install
```

### Step 3 — Infrastructure (Optional — Full Mode Only)

Only needed for live Qdrant vector search and Neo4j graph traversal:

```bash
# From esp_agent/ directory
docker-compose up -d

# Verify all containers running
docker-compose ps
```

---

## Configuration

Copy the example environment file:

```bash
cd esp_agent
cp .env.example .env
```

Edit `.env` with your settings:

```dotenv
# LLM Gateway (llama.cpp local server)
LLM_GATEWAY_URL=http://localhost:8080/v1
LLM_MODEL_NAME=qwen2.5-3b-instruct
LLM_TIMEOUT_SEC=60
LLM_MAX_RETRIES=3
# LLM_OFFLINE is disabled by project policy — the real local LLM server is always used.
# Do not set this variable; it has no effect (see src/llm/gateway.py).

# Vector DB
QDRANT_URL=http://localhost:6333

# Graph DB
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# Relational DB
POSTGRES_URL=postgresql://localhost:5432/esp_agent
```

---

## Running the Application

All **5 services** must run simultaneously. Open **5 separate terminal windows**.

### Windows PowerShell

#### Terminal 1 — Telemetry API (Port 8081)
```powershell
cd X:\TAS\Agentic_project\esp_agent
.venv\Scripts\Activate.ps1
python -m src.api.telemetry_mock_server
```
Expected: `Uvicorn running on http://0.0.0.0:8081`

---

#### Terminal 2 — ML Model API (Port 8082)
```powershell
cd X:\TAS\Agentic_project\esp_agent
.venv\Scripts\Activate.ps1
python -m src.api.ml_model_mock_server
```
Expected: `Uvicorn running on http://0.0.0.0:8082`

---

#### Terminal 3 — Engineering Service API (Port 8083)
```powershell
cd X:\TAS\Agentic_project\esp_agent
.venv\Scripts\Activate.ps1
python -m src.api.engineering_service_server
```
Expected: `Uvicorn running on http://0.0.0.0:8083`

---

#### Terminal 4 — FastAPI BFF Gateway (Port 8000)

**The local LLM server (llama.cpp on port 8080) MUST be running before this step.**
Offline/mock mode is disabled by project policy — the gateway always uses the real LLM.

```powershell
cd X:\TAS\Agentic_project\esp_agent
.venv\Scripts\Activate.ps1
python -m src.main
```
Expected: `Uvicorn running on http://0.0.0.0:8000`

---

#### Terminal 5 — cced_esp React Frontend (Port 3000/5173)
```powershell
cd X:\TAS\Agentic_project\cced_esp\frontend-react
npm run dev
```
This is the **main application UI** — the SCADA/ESP operations dashboard. `esp_agent` has no frontend of its own.

---

### Linux / macOS Bash

```bash
# Terminal 1 — Telemetry
cd esp_agent && source .venv/bin/activate && python -m src.api.telemetry_mock_server

# Terminal 2 — ML Model
cd esp_agent && source .venv/bin/activate && python -m src.api.ml_model_mock_server

# Terminal 3 — Engineering
cd esp_agent && source .venv/bin/activate && python -m src.api.engineering_service_server

# Terminal 4 — BFF Gateway (real local LLM must already be running on :8080)
cd esp_agent && source .venv/bin/activate && python -m src.main

# Terminal 5 — Frontend (main application UI)
cd cced_esp/frontend-react && npm run dev
```

---

### Access the Application

Open your browser at the URL printed by the `cced_esp/frontend-react` dev server (typically `http://localhost:3000` or `http://localhost:5173`). This is the ESP Operations Center dashboard — telemetry, envelope monitoring, diagnostics, and the Agent Jane advisory panel are all served from this single frontend.

---

## Health Check

Run in a new terminal after starting all services to verify everything is up:

**PowerShell:**
```powershell
$endpoints = @(
    "http://localhost:8081/health",
    "http://localhost:8082/api/v1/models/health",
    "http://localhost:8083/health",
    "http://localhost:8000/health",
    "http://localhost:3000/workspace/FS-031"
)
foreach ($ep in $endpoints) {
    try {
        $r = Invoke-WebRequest -Uri $ep -Method GET -TimeoutSec 5
        Write-Host "$ep -> HTTP $($r.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "$ep -> FAILED" -ForegroundColor Red
    }
}
```

**Bash / curl:**
```bash
for ep in \
  "http://localhost:8081/health" \
  "http://localhost:8082/api/v1/models/health" \
  "http://localhost:8083/health" \
  "http://localhost:8000/health" \
  "http://localhost:3000/workspace/FS-031"; do
    code=$(curl -o /dev/null -s -w "%{http_code}" "$ep")
    echo "$ep -> HTTP $code"
done
```

All five should return `HTTP 200`.

---

## Running Tests

The test suite has **48 test files** covering all platform layers.

```bash
cd esp_agent

# Run all tests
python -m pytest tests/ -v

# Engineering Calculation Engine (9 tests)
python -m pytest tests/test_engineering_service.py -v

# Telemetry API
python -m pytest tests/test_telemetry_mock_api.py -v

# ML Model Integration
python -m pytest tests/test_ml_model_integration.py -v

# LLM Gateway Layer
python -m pytest tests/test_phase10_llm_layer.py -v

# FastAPI BFF routes
python -m pytest tests/test_fastapi.py tests/test_phase9_bff_routes.py -v

# Full Phase 1-5 Architecture
python -m pytest tests/test_phase1_architecture.py tests/test_phase2_contracts.py \
  tests/test_phase3_kb.py tests/test_phase4_objective_layer.py \
  tests/test_phase5_golden_scenarios.py -v
```

### Automated Browser UI Test (Playwright)

```bash
# Requires all 5 services to be running first
cd esp_agent
python tests/run_ui_live_browser_test.py
```

---

## Offline / LLM-Free Mode — DISABLED BY PROJECT POLICY

`LLM_OFFLINE` no longer has any effect. The gateway always calls the real local LLM
server (llama.cpp on port 8080). Setting `LLM_OFFLINE=1` in the environment is ignored
(a warning is logged) — see `src/llm/gateway.py`.

If the LLM server is genuinely unreachable at request time, `LLMGateway.chat()` still
falls back to a deterministic mock response automatically as a runtime *availability*
safeguard — that is unrelated to this env var and cannot be toggled on intentionally.

Engineering calculations (A1-G3) and ML mock inference remain fully deterministic
regardless of LLM availability, as before.

---

## API Reference

### FastAPI BFF Gateway — Port 8000

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/ui/assets` | List all ESP assets |
| `GET` | `/api/ui/assets/{assetId}/workspace` | Get asset workspace context |
| `POST` | `/api/ui/agent/stream` | **NDJSON streaming agent run** |
| `POST` | `/api/ui/agent/query` | Synchronous agent query |
| `GET` | `/docs` | Swagger UI |

### Telemetry API — Port 8081

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/assets` | List all monitored assets |
| `GET` | `/api/v1/assets/{assetId}/telemetry/current` | Latest telemetry snapshot |
| `GET` | `/api/v1/assets/{assetId}/telemetry/history` | Historical telemetry |
| `GET` | `/docs` | Swagger UI |

### ML Model API — Port 8082

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/models/health` | Health check |
| `POST` | `/api/v1/models/fault-classification` | Fault classification inference |
| `POST` | `/api/v1/models/risk-prediction` | 24-hour risk score prediction |
| `GET` | `/api/v1/models/status` | Model version & status |
| `GET` | `/docs` | Swagger UI |

### Engineering Service API — Port 8083

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/engineering/calculate` | Run deterministic engineering calculation |
| `GET` | `/api/v1/engineering/calculations` | List available calculations (A1-G3) |
| `GET` | `/api/v1/engineering/oem/{pumpModel}` | Get OEM pump curve data |
| `GET` | `/docs` | Swagger UI |

---

## Generative UI Workspace

The workspace is built on **Next.js 16 App Router** with a floating, resizable **Agent Jane** dialog system.

### Dialog Features

- **Floating, resizable** — drag to reposition, expand/collapse between compact (480px) and wide (740px) mode
- **NDJSON streaming** — real-time token streaming from the multi-agent backend
- **Generative UI Blocks** rendered dynamically:
  - `MarkdownBlock` — GitHub-flavoured markdown with code highlighting
  - `PlotlyChartBlock` — interactive Plotly.js charts embedded inline
  - `StatusBannerBlock` — workflow milestone banners
  - `ActionCardBlock` — recommended operator action cards
- **Quick Prompt Chips** — pre-configured diagnostic shortcuts:
  - "Diagnose drawdown & motor temp"
  - "Analyze intake gas interference"
  - "Check pump efficiency degradation"

### Key Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| `@assistant-ui/react` | ^0.15 | AI chat UI components & streaming |
| `@assistant-ui/react-langgraph` | ^0.14 | LangGraph to UI adapter |
| `ai` (Vercel AI SDK) | ^7.0 | Streaming, structured outputs |
| `react-plotly.js` | ^4.1 | Interactive engineering charts |
| `react-markdown` | ^10.1 | Markdown rendering in dialog |
| `remark-gfm` | ^4.0 | GitHub Flavored Markdown support |
| `react-resizable-panels` | ^4.12 | Drag-to-resize layout panels |

---

## Agent Architecture

```
User Query
    |
    v
Intent Router (classify query intent)
    |
    v
Supervisor Graph
    +-- ReliabilitySpecialist    <- ML model outputs, failure risk, RUL
    +-- EngineeringSpecialist    <- Physics calculations (A1-G3), OEM curves
    +-- WellPerformanceSpecialist <- Production rate, drawdown, inflow
    +-- DigitalTwinSpecialist    <- Virtual ESP state estimation
    +-- MaintenanceSpecialist    <- Work order generation, maintenance planning
    +-- KnowledgeSpecialist      <- RAG document retrieval, precedent search
```

### Design Principles

- **LLM is NOT the calculation authority** — all physics formulas execute in the deterministic engine
- **Fail-closed policy** — missing required parameters (SG, Water Cut) block calculations rather than assume defaults
- **Evidence-packing** — every advisory is backed by traceable data provenance
- **Offline-first** — full diagnostic capability without external LLM dependency

---

## Engineering Calculation Engine

Implemented in `esp_agent/src/services/engineering/engine.py`:

| Code | Formula | Description |
|------|---------|-------------|
| **A1** | `H = (2.31 x dP) / SG` | Pressure to Head conversion (ft) |
| **A2** | `P_hyd = (Q x H x SG) / 3960` | Hydraulic Power (hp) |
| **A4** | `Q_adj = Q x (f/60)` / `H_adj = H x (f/60)^2` | Affinity Laws (VSD frequency) |
| **A5** | `%BEP = Q_operating / Q_BEP_at_freq x 100` | Best Efficiency Point % |
| **B1** | OEM curve interpolation | Pump head curve at operating frequency |
| **C2** | `%Load = I_measured / I_nameplate x 100` | Motor Load % |
| **E1** | Shaft power & efficiency | Pump efficiency from OEM curves |
| **F1** | Wear rate estimation | Bearing & impeller wear model |

**OEM Pump Models Supported:**
- Baker Hughes D1450
- Schlumberger DN1750
- M500 Motor series

---

## ML Model Integration

ML adapter at `esp_agent/src/adapters/ml_model_adapter.py` consumes v2.0.0 output contracts:

| Model | Outputs | Description |
|-------|---------|-------------|
| Fault Classifier | `fault_type`, `confidence`, `severity` | Multi-class fault classification |
| Risk Predictor | `risk_score_24h`, `risk_score_72h`, `rul_days` | Remaining Useful Life & risk horizon |

Integration flow:
```
POST /api/v1/models/fault-classification -> ReliabilitySpecialist
POST /api/v1/models/risk-prediction      -> ReliabilitySpecialist
```

---

## Troubleshooting

### Port Already in Use

```powershell
# Find and kill a process on a port (Windows)
netstat -ano | findstr :8081
taskkill /PID <PID_NUMBER> /F
```

### Python Module Not Found

```bash
cd esp_agent
pip install -e .
```

### Frontend Build Errors / Stale Cache

```bash
cd cced_esp/frontend-react
rm -rf node_modules dist
npm install
npm run dev
```

### `Failed to fetch workspace for FS-031`

The FastAPI BFF Gateway (port 8000) is not running. Verify:

```bash
curl http://localhost:8000/health
```

### LLM Timeout Errors

`LLM_OFFLINE` is disabled by policy and will not help here. Instead:
1. Confirm llama.cpp is running and healthy: `curl http://localhost:8080/health`
2. Increase `LLM_TIMEOUT_SEC` / `LLM_MAX_RETRIES` in `.env` if the model is slow to respond
   (CPU inference of a cold model can take 20-40s per call).

### Streaming Agent Request Failed

Verify the BFF streaming endpoint:

```bash
curl -X POST http://localhost:8000/api/ui/agent/stream \
  -H "Content-Type: application/json" \
  -d '{"assetId": "FS-031", "query": "Run diagnostics"}'
```

---

## Documentation Index

| Document | Path | Contents |
|----------|------|---------|
| Engineering Service Architecture | `docs/architecture/ESP_APM_Engineering_Service_Architecture_Granular_Design.docx` | Calc engine design |
| ML Model Integration Design | `docs/architecture/ESP_APM_ML_Model_Integration_and_Consumption_Design.docx` | ML contracts |
| Evidence Pack Design (Phase 8) | `docs/architecture/ESP_APM_PHASE_8_Evidence_Pack_Agent_Context_Implementation_Design.docx` | Context & evidence |
| Frontend/Backend Integration (Phase 9) | `docs/architecture/ESP_APM_PHASE_9_FRONTEND_BACKEND_PRODUCT_INTEGRATION_ARCHITECTURE.docx` | API & UI design |
| Telemetry Mock API Spec | `docs/architecture/ESP_APM_Telemetry_Mock_API_Specification.docx` | Mock data contracts |
| Telemetry Consumption Architecture | `docs/architecture/ESP_APM_Telemetry_Service_Consumption_Architecture.docx` | Telemetry design |
| ML Team Dependencies | `docs/specifications/ESP_Agentic_ML_Team_Dependencies_and_API_PreRequisites.md` | ML API contract |
| Engineering Research Package | `docs/specifications/ESP_Engineering_Research_Package.md` | ESP physics reference |
| Dependency Detail | `docs/specifications/dependency_detail.md` | Service dependencies |

---

## License

Internal — ESP APM Agentic Platform — TAS Engineering Division

---

*Last updated: 2026-08-27 | Platform v1.0.0*
