# ⚡ ESP APM — Autonomous Industrial AI Platform

> **Autonomous AI Agentic Engineering, Diagnostic & Conversational Co-Pilot for Electrical Submersible Pumps (ESP)**
> Built with LangGraph Supervisor multi-agent orchestration, deterministic physics calculation engines, dual-tier ML inference, live MQTT SCADA ingestion, and real-time React streaming UI.

---

## 📋 Table of Contents

1. [Executive Overview](#-executive-overview)
2. [End-to-End System Architecture](#-end-to-end-system-architecture)
3. [Microservices & Active Port Map](#-microservices--active-port-map)
4. [What Has Been Built (Phase-by-Phase Roadmap)](#-what-has-been-built-phase-by-phase-roadmap)
   - [Live MQTT Telemetry & Historian Pipeline](#1-live-mqtt-telemetry--historian-pipeline)
   - [Dual-Tier Machine Learning & VFD Diagnostics](#2-dual-tier-machine-learning--vfd-diagnostics)
   - [Level A: Conversational Memory & Implicit Resolution](#3-level-a-conversational-memory--implicit-resolution)
   - [Level B: HITL Clarification & Intelligent Routing](#4-level-b-hitl-clarification--intelligent-routing)
   - [Level C: Durability & Long-Term Well Memory](#5-level-c-durability--long-term-well-memory)
   - [ML Telemetry Polling API (Secure Historical Access)](#6-ml-telemetry-polling-api-secure-historical-access)
   - [Local CUDA GPU LLM Acceleration (RTX 3050)](#7-local-cuda-gpu-llm-acceleration-rtx-3050)
5. [Quickstart: Single-Laptop Operation](#-quickstart-single-laptop-operation)
6. [Detailed CLI Command Guide](#-detailed-cli-command-guide)
   - [Multi-Service Launcher](#1-multi-service-launcher)
   - [Historian Query CLI](#2-historian-query-cli)
   - [Verifying Endpoints with cURL](#3-verifying-endpoints-with-curl)
7. [Running the Test Suites](#-running-the-test-suites)
8. [Directory & Repository Structure](#-directory--repository-structure)
9. [Git Deployment & Submodule Synchronization](#-git-deployment--submodule-synchronization)
10. [Troubleshooting & FAQ](#-troubleshooting--faq)

---

## 🚀 Executive Overview

The **ESP APM Platform** is an enterprise-grade artificial intelligence supervisory co-pilot (**Agent Jane**) designed for oil & gas production operators and artificial lift engineers. 

Unlike conventional chatbots, Agent Jane combines:
- **Deterministic Engineering Calculations**: Dynamic total dynamic head (TDH), pump hydraulic performance curves, electrical motor slip, and gas volume fraction (GVF).
- **Dual-Tier ML Diagnostics**: Offline well calibration baseline models coupled with real-time Variable Frequency Drive (VFD) anomaly classifiers across 14 high-frequency parameters.
- **Fail-Closed Safety Engine (OP00)**: Autonomous physical control refusal policy enforcing advisory-only boundaries.
- **Stateful Multi-Turn Memory**: Cross-turn context tracking, implicit asset resolution, and cross-session per-well episodic memory.
- **Human-In-The-Loop (HITL) Interrupts**: Self-gating clarification routing that pauses graph execution in `<10s` for ambiguous operator inquiries rather than running expensive analysis on the wrong asset.

---

## 🏗️ End-to-End System Architecture

```
                                  +---------------------------------------+
                                  |     REACT FRONTEND (Vite / React 18)  |
                                  |  - Real-Time Telemetry Dashboard      |
                                  |  - Agent Floating Dock & Chat Drawer  |
                                  |  - NDJSON Token Streaming Parser      |
                                  |  - Plotly Interactive Charts          |
                                  |         http://localhost:3000         |
                                  +-------------------+-------------------+
                                                      |
                         +----------------------------+----------------------------+
                         | (REST / SSE Telemetry)                                  | (NDJSON Agent Runs & Clarifications)
                         v                                                         v
       +------------------------------------+                    +------------------------------------+
       |   CORE CCED_ESP BACKEND (FastAPI)  |                    |      AGENT JANE BFF GATEWAY        |
       | - REST & SSE Telemetry Endpoints   |                    | - User Entry Adapter (v7.0)        |
       | - Live VFD Diagnostic Service      |                    | - Session Intent Routing           |
       | - SQLite Recovery Historian        |                    | - Clarification Pending Cache      |
       |       http://localhost:8000        |                    |       http://localhost:8090        |
       +-----------------+------------------+                    +-----------------+------------------+
                         |                                                         |
                         | (Ingestion)                                             | (LangGraph Execution)
                         v                                                         v
       +------------------------------------+                    +------------------------------------+
       |        MQTT BROKER (Mosquitto)     |                    |    LANGGRAPH SUPERVISOR GRAPH      |
       | - Topic: cced/esp/telemetry/live   |                    | - Route Objective Node             |
       | - 14 High-Frequency VFD Parameters |                    | - HITL Clarification Node          |
       |          localhost:1883            |                    | - Multi-Specialist Dynamic Loop    |
       +------------------------------------+                    | - Compact Context Builder          |
                                                                 +-----------------+------------------+
                                                                                   |
            +----------------------------------------------------------------------+
            |                         |                          |
            v                         v                          v
+-----------------------+ +-----------------------+ +-----------------------+
|    REDIS (Port 6379)  | |   QDRANT (Port 6333)  | |  CUDA GPU LLM SERVER  |
| - ConversationStore   | | - esp_kb Collection   | | - llama-server :8080  |
| - RedisCheckpointer   | | - Vector Embeddings   | | - Qwen2.5-Coder-3B    |
| - WellEpisodicMemory  | | - OEM Manual RAG      | | - RTX 3050 CUDA / GPU |
+-----------------------+ +-----------------------+ +-----------------------+
```

---

## 🔌 Microservices & Active Port Map

| Port | Service Name | Directory / Module | Purpose |
|---|---|---|---|
| `:3000` | **React Frontend** | `cced_esp/frontend-react` | Operator UI, live asset telemetry, Agent Jane dock |
| `:8000` | **Core Backend API** | `cced_esp/backend/main.py` | Telemetry REST API, SSE stream, VFD diagnostics |
| `:8090` | **Agent Jane BFF** | `esp_agent/run_agent_server.py` | FastAPI gateway for LangGraph agent runs & streaming |
| `:1883` | **MQTT Broker** | Mosquitto | Pub/sub broker for real-time ESP pump telemetry |
| `:8080` | **LLM Inference Server** | `bin/llama-cpp/llama-server.exe` | Local CUDA GPU GGUF inference (RTX 3050 CUDA 12.4) |
| `:6379` | **Redis Cache & Memory** | Redis Server | Session memory, LangGraph checkpoints, well history |
| `:6333` | **Qdrant Vector DB** | Qdrant Engine | Knowledge base embeddings (`esp_kb`) for RAG retrieval |
| `:7474` / `:7687` | **Neo4j Graph DB** | Neo4j | Equipment topology and failure mode knowledge graph |

---

## 🛠️ What Has Been Built (Phase-by-Phase Roadmap)

### 1. Live MQTT Telemetry & Historian Pipeline
- **14 VFD Telemetry Channels**: Ingests high-resolution electrical and hydraulic telemetry:
  - `frequency`, `motor_current`, `voltage`, `active_power`, `power_factor`
  - `intake_pressure` (PIP), `discharge_pressure` (PDP), `motor_temperature`, `vibration_x/y`
  - `flow_rate`, `choke_position`, `drive_frequency_reference`, `output_torque`
- **Zero-Loss Live Historian (`cced_esp/data/unlabelled.db`)**: High-speed SQLite ingestion continuously populated via live broker injection with over 2,685,000+ historical records. Multi-column covering indexes (`asset_id`, `timestamp`) allow instantaneous sub-10ms range scans.
- **Historian Query Utility (`esp_agent/query_historian.py`)**: CLI and API tool that parses plain-English questions into bounded SQL queries against `unlabelled.db`, computes statistical rollups, detects inflection points, and extracts source-cited Level-D ground-truth evidence packs.

### 2. Dual-Tier Machine Learning & VFD Diagnostics
- **Single Source of Truth (`code/models/`)**: Fully consolidated, zero-syntax-error ML engine located in `code/models/` (legacy `ESP_APM_models/` retired):
  - `WellDiagnosticEngine`: Live orchestrator with dynamic normalization and dynamic head ($\Delta P$) engineering.
  - `SiteTelemetryAdapter`: Bridges raw SCADA keys into canonical 14-parameter vectors with well-calibrated fallback envelopes.
  - `WellCalibrationRegistry`: Pre-computed statistical envelopes across 73 individual CCED wells (`well_calibration_registry.json`).
  - `FaultClassificationEngine`: 13-fault mode classifier including Phase Imbalance ($I_{\text{imb}}, V_{\text{imb}}$), Dry-Well Pump Off, Blocked Intake, Sand Ingestion, Bearing Degradation, and Motor Overload.
  - `MultivariateAnomalyDetector`: Statistical outlier detector flagging abnormal multi-sensor operating states.
- **Online VFD Diagnostic Engine (`cced_esp/backend/services/vfd_diagnostic_service.py`)**:
  - Automatically processes live MQTT payloads, computes health indices ($0-100$), generates pretty Operator Diagnostic Intelligence Cards to console, and appends durable audit logs to `cced_esp/data/logs/vfd_diagnostics.jsonl`.
  - Injected directly into the supervisor context as structured evidence (`EVID-VFD-*`).

### 3. Level A: Conversational Memory & Implicit Resolution
- **Redis `ConversationStore` (`esp_agent/src/memory/conversation_store.py`)**:
  - Key: `esp:conv:{session_id}`, 7-day TTL, capped at 20 turns, serves last 10.
  - Graceful in-memory fallback if Redis is temporarily unavailable.
- **Frontend Identity Tracking (`X-Session-ID`)**:
  - `agentApi.js` generates and persists a session UUID in `localStorage` across page navigations and tabs.
- **Implicit Asset Resolution**:
  - When an operator asks a follow-up (e.g. *"is that bad?"* or *"what should I do?"*) without re-specifying the well name, `IntentRouter` and `UserEntryAdapter` resolve the well ID and prior objective from conversation context without defaulting to random assets.

### 4. Level B: HITL Clarification & Intelligent Routing
- **Ambiguity Scoring (`RouteResult.is_ambiguous`)**:
  - Evaluates semantic confidence (`<0.65`) combined with absence of well context to flag queries as ambiguous.
  - Prevents the legacy silent-default bug where vague queries automatically executed `OP03_FAULT_DIAGNOSIS`.
- **LangGraph `clarification_node` & Interrupts**:
  - Interrupts graph execution before expensive specialist calculations or LLM calls run (`<10s` turnaround).
  - Emits clarification questions (e.g., *"Which well are you asking about — FS-031 or FSWS-001-A?"*).
  - Operator answer resumes the identical paused thread via `Command(resume=answer)`.
- **14-Objective LLM Classifier Fallback (`_llm_classify`)**:
  - Calls local LLM with constrained prompt when keyword and semantic scores are low.
  - Short-circuits when Path A deterministic rules already match (sub-2s latency).
  - Refined greeting filter ensures operational queries (e.g., *"morning, can you take a look at things?"*) route to status/fault checks rather than small talk.

### 5. Level C: Durability & Long-Term Well Memory
- **Per-Well Episodic Store (`WellEpisodicMemoryStore`)**:
  - Persists rolling summaries in Redis under `esp:well_memory:{well_id}` with a 30-day TTL.
  - Tracks total assessments, last diagnosis, last recommendation, and the rolling 5 most recent diagnostic events.
- **Context Injection (`CompactContextBuilder`)**:
  - Injects `compact["episodic_well_memory"]` into the LLM context.
  - When an operator opens a brand-new browser session on `FSWS-001-A`, Agent Jane recalls: *"Previous Operational Memory for FSWS-001-A: Last assessed on 2026-09-02 (High Backpressure). Recommendation: Inspect surface choke."*
- **Restart-Safe LangGraph Checkpointer (`RedisCheckpointer`)**:
  - Subclasses `MemorySaver`, serializing checkpoint states, blobs, and writes to Redis (`esp:lg_check:{thread_id}`) via base64-encoded binary payloads (7-day TTL).
  - Re-hydrates interrupted threads across backend process restarts, enabling true restart-safe HITL continuation.

### 6. Local CUDA GPU LLM Acceleration (RTX 3050)
- **Zero External API Dependency**:
  - Powered by local `bin/llama-cpp/llama-server.exe` with NVIDIA CUDA 12.4 runtime (`ggml-cuda.dll`, `cublas64_12.dll`).
  - Benchmarked on NVIDIA GeForce RTX 3050: **Prompt processing: 1,801 tok/s** | **Generation: 58 tok/s**.
  - Default model: `models/Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf`.
  - 1-Click launcher: `start_gpu_llm.bat` (launches server on `http://127.0.0.1:8080/v1`).

---

## 💻 Quickstart: Single-Laptop Operation

To operate the entire platform locally on a single workstation or laptop:

### Prerequisites
1. **Windows 10/11** or **Ubuntu 22.04+**
2. **Python 3.10+** (with virtual environment created in `esp_agent/.venv` and `cced_esp/.venv`)
3. **Node.js 18+ & npm**
4. **Redis Server** running locally on port `6379`
5. **Mosquitto MQTT Broker** running locally on port `1883`
6. **Local LLM Engine** (`llama-server` running Qwen2.5-Coder-3B or compatible OpenAI-compatible endpoint)

### One-Command Full Startup
Run the unified multi-service supervisor script from the project root:

```powershell
# From the project root (X:\TAS\Agentic_project)
python run_all_services.py
```
*(Or double-click `start_all_services.bat` on Windows)*

This script boots and monitors:
1. **Core Backend** on `http://localhost:8000`
2. **Agent Jane BFF** on `http://localhost:8090`
3. **React Frontend** on `http://localhost:3000`
4. **MQTT Telemetry Publisher** feeding live 14-parameter data

Once running, navigate your browser to **`http://localhost:3000`**.

---

## 📖 Detailed CLI Command Guide

### 1. Multi-Service Launcher

To run individual components manually in separate terminal windows:

```powershell
# Window 1: Start Redis & Mosquitto (if installed as services, skip this)
redis-server
mosquitto -v

# Window 2: Start Core Backend (cced_esp)
cd X:\TAS\Agentic_project\cced_esp
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Window 3: Start Agent Jane BFF (esp_agent)
cd X:\TAS\Agentic_project\esp_agent
.venv\Scripts\python.exe run_agent_server.py --port 8090

# Window 4: Start React Frontend
cd X:\TAS\Agentic_project\cced_esp\frontend-react
npm run dev

# Window 5: (Optional) Publish Live MQTT Telemetry Stream
cd X:\TAS\Agentic_project\cced_esp
.venv\Scripts\python.exe src/mqtt_publisher.py
```

---

### 2. Historian Query CLI

Query the live SQLite telemetry database (`cced_esp/data/unlabelled.db`) using natural language:

```powershell
cd X:\TAS\Agentic_project\esp_agent

# Run a 6-hour production decline investigation on FS-031
.venv\Scripts\python.exe query_historian.py --query "Why is production declining on FS-031 in the last 6 hours?" --export-json

# Evaluate thermal stress on FS-010 over past 24 hours
.venv\Scripts\python.exe query_historian.py --query "Evaluate thermal stress and motor temperature on FS-010 over past 24 hours" --window 24h --export-json
```

---

### 3. Verifying Endpoints with cURL

#### Health Check
```powershell
# Core Backend
curl http://localhost:8000/health

# Agent Jane BFF
curl http://localhost:8090/health
```

#### Synchronous Agent Advisory (`/api/ui/agent/run`)
```powershell
curl -X POST http://localhost:8090/api/ui/agent/run `
  -H "Content-Type: application/json" `
  -H "X-Session-ID: sess-test-12345" `
  -d '{
    "asset_id": "FSWS-001-A",
    "user_query": "What is the current status and health index?"
  }'
```

#### Streaming Agent Advisory (`/api/ui/agent/stream`)
```powershell
curl -N -X POST http://localhost:8090/api/ui/agent/stream `
  -H "Content-Type: application/json" `
  -H "X-Session-ID: sess-test-12345" `
  -d '{
    "asset_id": "FSWS-001-A",
    "user_query": "Is there any gas interference?"
  }'
```

#### Test Ambiguous Clarification Trigger
```powershell
curl -X POST http://localhost:8090/api/ui/agent/run `
  -H "Content-Type: application/json" `
  -H "X-Session-ID: sess-clarif-test" `
  -d '{
    "asset_id": null,
    "user_query": "morning, can you take a look at things?"
  }'
---

## 🧪 Running the Test Suites

All test suites can be executed using the project Python virtual environment:

```powershell
# 1. Run 13-Fault Scenario ML Validation Suite (15/15 scenarios)
esp_agent\.venv\Scripts\python.exe code/models/test_fault_scenarios.py

# 3. Run Level A Tests (Conversational Memory & Context)
cd X:\TAS\Agentic_project\esp_agent
.venv\Scripts\python.exe -m pytest tests/test_plan_level_a_conversation_memory.py -v

# 4. Run Level B Tests (Ambiguity Scoring & HITL Clarification)
.venv\Scripts\python.exe -m pytest tests/test_plan_level_b_clarification_routing.py -v
.venv\Scripts\python.exe -m pytest tests/test_plan_level_b_conversation.py -v

# 5. Run Level C Tests (Well Episodic Durability & Restart Safety)
.venv\Scripts\python.exe -m pytest tests/test_plan_level_c_durability.py -v
```

---

## 📂 Directory & Repository Structure

```
X:\TAS\Agentic_project
│
├── Plan.md                                <- Authoritative multi-phase delivery specification
├── README.md                              <- Project Master Documentation (This file)
├── run_all_services.py                    <- Unified multi-process launcher for all servers
├── start_all_services.bat                 <- Windows batch launcher (CUDA LLM + Core + BFF + Frontend)
├── start_gpu_llm.bat                      <- Standalone 1-click CUDA GPU llama-server launcher (:8080)
├── stop_all_services.bat                  <- Clean teardown script for all running background processes
│
├── bin/
│   └── llama-cpp/                         <- Pre-compiled CUDA 12.4 llama-server & runtime DLLs
│
├── cced_esp/                              <- Core Backend & React Frontend Submodule
│   ├── backend/
│   │   ├── main.py                        <- FastAPI Core Server (:8000)
│   │   ├── mqtt_collector.py              <- Live MQTT Subscriber daemon
│   │   ├── transformer.py                 <- VFD 14-signal canonical resolution & telemetry parsing
│   │   ├── api/
│   │   └── services/
│   │       └── vfd_diagnostic_service.py  <- 14-parameter VFD heuristic classifier & JSONL logger
│   ├── frontend-react/                    <- Vite + React 18 UI (:3000)
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   └── AgentFloatingDock.jsx  <- Agent Jane streaming chat drawer
│   │   │   ├── context/TelemetryContext.jsx
│   │   │   └── services/agentApi.js       <- Session ID & streaming API client
│   │   └── package.json
│   ├── data/
│   │   ├── unlabelled.db                  <- Sole live SQLite telemetry store (2.68M+ records)
│   │   ├── labelled.db                    <- Ground-truth labelled training scenarios
│   │   └── logs/
│   │       └── vfd_diagnostics.jsonl      <- Append-only durable VFD evaluation audit log
│   └── src/                               <- Legacy inference & MQTT publisher
│
├── esp_agent/                             <- Agent Jane Orchestration Core
│   ├── run_agent_server.py                <- BFF Gateway Server entrypoint (:8090)
│   ├── query_historian.py                 <- Natural language SQLite historian utility
│   ├── src/
│   │   ├── agent/
│   │   │   ├── intent_router.py           <- 3-path router + ambiguity scorer + LLM fallback
│   │   │   ├── objective_registry.py      <- 14 Level-2 objectives registry
│   │   │   └── supervisor/
│   │   │       ├── graph.py               <- LangGraph Supervisor state graph + clarification node
│   │   │       ├── user_entry.py          <- UserEntryAdapter (v7.0) with pause/resume contracts
│   │   │       └── state.py               <- AgentState TypedDict schema
│   │   ├── memory/
│   │   │   ├── conversation_store.py      <- Level A: Per-session Redis sliding memory
│   │   │   ├── well_memory.py             <- Level C: Per-well episodic long-term store
│   │   │   └── redis_checkpointer.py      <- Level C: Restart-safe LangGraph checkpointer
│   │   ├── llm/
│   │   │   ├── gateway.py                 <- Local GPU LLM client (Qwen2.5-Coder-3B :8080)
│   │   │   ├── context_builder.py         <- Compact context compressor for 4B models
│   │   │   └── adapter.py                 <- Pydantic advisory schema generator
│   │   └── api/rest/
│   │       └── bff_routes.py              <- UI REST & SSE streaming endpoints
│   └── tests/                             <- Full Agent Jane unit & integration test suites
│
├── code/                                  <- Canonical ML Models & Data Science Tools (Single Source of Truth)
│   ├── models/                            <- 13-Fault Diagnostic Engine & Calibration Baselines
│   │   ├── diagnostic_engine.py           <- WellDiagnosticEngine with SiteTelemetryAdapter
│   │   ├── telemetry_adapter.py           <- SiteTelemetryAdapter (14-parameter normalizer)
│   │   ├── calibration_registry.py        <- 73-well statistical baselines
│   │   ├── fault_classifier.py            <- 13-fault mode classifier + imbalance scoring
│   │   ├── anomaly_detector.py            <- Multivariate anomaly detection
│   │   ├── test_fault_scenarios.py        <- 15-scenario validation suite (100% pass)
│   │   └── well_calibration_registry.json <- Pre-computed 73-well calibration envelopes
│   ├── eda/                               <- Streamlit & Plotly interactive analysis tools
│   ├── categorize_and_normalize_ml.py     <- Offline batch categorization pipeline
│   └── merge_excel.py                     <- High-performance SCADA Excel stacker
│
├── tests/
│   └── test_ml_telemetry_api.py           <- 7-test integration suite for ML Telemetry API
│
└── models/                                <- Local LLM GGUF model storage (Git-ignored)
    ├── Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf
    ├── Qwen3-4B-Q4_K_M.gguf
    └── microsoft_Phi-4-mini-instruct-Q4_K_M.gguf
```

---

## 🔄 Git Deployment & Synchronization

The repository consists of a **Root Repository** (`Agentic_project`) and an embedded **Submodule** (`cced_esp`).

### Pushing Changes Safely
Always push the submodule first before updating the root pointer:

```powershell
# 1. Commit and push the submodule (cced_esp)
cd X:\TAS\Agentic_project\cced_esp
git add -A
git commit -m "feat: backend and frontend updates"
git push origin main

# 2. Commit and push the root repository (Agentic_project)
cd X:\TAS\Agentic_project
git add Plan.md README.md cced_esp esp_agent/ code/ tests/ bin/
git commit -m "feat: consolidate ml models into code and add gpu telemetry api"
git push origin dev
```

### Cloning onto a New Machine
```powershell
git clone --recursive -b dev https://github.com/ritisha2/Agentic_project.git
cd Agentic_project
git submodule update --init --recursive
```

---

## ❓ Troubleshooting & FAQ

#### 1. Why does an ambiguous query like *"morning, take a look"* not run diagnostics?
This is an intentional Level B feature. In industrial oilfields with dozens of ESP pumps, executing a 60-second diagnostic run without a specified well could generate false alarms on the wrong asset. Agent Jane pauses via `clarification_node` in `<10s` and prompts you for the target well.

#### 2. Where are the `.gguf` model files?
Because GitHub imposes a strict 100MB file size limit, `.gguf` binary weights (>2GB) are excluded via `.gitignore`. Place them in `<ProjectRoot>/models/` manually or pull them from your team's internal model registry.

#### 3. How do I clear conversation or well memory for testing?
To wipe Redis memory keys:
```powershell
# Open redis-cli and flush specific patterns:
redis-cli --scan --pattern "esp:*" | xargs redis-cli del
# Or flush entire local Redis:
redis-cli flushall
```

#### 4. `TypeError: 'NoneType' object is not callable` in `LLMGateway`
Ensure your local `llama-server` is listening at the URL specified in `esp_agent/.env` (`LLM_GATEWAY_URL=http://localhost:8080/v1` or office server IP). Verify health via:
```powershell
curl http://localhost:8080/health
```

---

## 📜 License & Operational Note

**Internal & Confidential** — CCED / TAS Engineering APM Project.  
All recommendations emitted by Agent Jane are strictly **ADVISORY-ONLY**. Direct control commands to VFD drives or surface chokes must be executed and verified by a licensed human field operator.
