# OPG CCED ESP APM & Multi-Agent Intelligence Platform
## Repository Architecture & Directory Structure Guide

> **Document Version:** 1.0.0  
> **Updated:** 2026-09-06  
> **Git Branch:** `fe`  
> **Target Audience:** Engineering, ML Teams, Frontend Developers, and Operations

---

## 1. High-Level System Architecture

The repository unites **three primary layers** over a **single shared telemetry & reference backend**:

```
                              ┌────────────────────────────────────────────────────────┐
                              │            SHARED TELEMETRY & REFERENCE BACKEND         │
                              │            (cced_esp/backend & cced_esp/data)          │
                              │  • Databases: labelled.db, unlabelled.db, normalized.db│
                              │  • Reference Artifacts: data/artifacts/ (Baselines/Sigs│
                              │  • Live Ingestion: MQTT Collector & VFD Live Bridge    │
                              └───────────────┬───────────────────────┬────────────────┘
                                              │                       │
                     ┌────────────────────────┴──────┐                │
                     ▼                               ▼                ▼
    ┌─────────────────────────────────┐   ┌─────────────────────┐  ┌─────────────────────┐
    │     STREAMLIT AGENT CHAT        │   │    REACT FRONTEND   │  │   EDA DASHBOARD     │
    │     (agent_streamlit.py)        │   │(cced_esp/frontend-r)│  │ (code/eda/dashboard)│
    │  • Conversational LangGraph UI  │   │• Real-time web app  │  │ • 10-tab diagnostic │
    │  • Inline Plotly 4-Visual Suite │   │• WebSocket ledger   │  │ • Tab 11 Forensics  │
    │  • Direct Python agent bridge   │   │• REST API client    │  │ • Research EDA      │
    └─────────────────────────────────┘   └─────────────────────┘  └─────────────────────┘
```

---

## 2. Directory Clubbing & Logical Organization

The repository is organized into five clean functional domains:

```
x:/TAS/Agentic_project/
├── 📘 Specifications & Plans (Root *.md)
├── 🤖 esp_agent/           (Multi-Agent Cognitive Supervisor & Specialists)
├── ⚙️ cced_esp/             (Core Backend, Real-Time Ingestion, ML Pipeline & React Client)
├── 🔬 code/                 (Offline ML Diagnostic Engine, EDA Dashboard & Figure Factory)
├── 📚 esp-knowledge/        (Domain Teardown Reports, API Standards & Docling Knowledge)
└── 🗄️ archive/              (Safely Archived Deprecated Scaffolds & External Sandboxes)
```

---

## 3. Detailed Folder Breakdown & Section Index

### Domain 1: Root System Entry Points & Specifications
Location: `/` (Root directory)

| File | Purpose & Function |
|---|---|
| [`agent_streamlit.py`](file:///x:/TAS/Agentic_project/agent_streamlit.py) | **Full-width conversational Agent UI**. Directly invokes `esp_agent` LangGraph graph, handles intent routing, renders operator responses, and renders inline Plotly forensic charts. |
| [`run_all_services.py`](file:///x:/TAS/Agentic_project/run_all_services.py) | Master multi-process launcher starting backend API, MQTT collector, and UI services simultaneously. |
| [`run_full_query_pipeline.py`](file:///x:/TAS/Agentic_project/run_full_query_pipeline.py) | End-to-end integration test harness querying across live database, asset service, and supervisor agent. |
| [`visual1.md`](file:///x:/TAS/Agentic_project/visual1.md) | **Visual 1 Spec:** Forensic Tipping Timeline (3-row synchronized time-series with $P_{10}\text{–}P_{90}$ corridors). |
| [`visual2.md`](file:///x:/TAS/Agentic_project/visual2.md) | **Visual 2 Spec:** Subsystem Health Equalizer (4 divergent balance bars) & Wellbore Pressure Depth Profile ($\Delta P = 0\text{ psi}$). |
| [`visual3.md`](file:///x:/TAS/Agentic_project/visual3.md) | **Visual 3 Spec:** In-Situ $H-Q$ Pump Performance Curve (Affinity Law scaling, ROR thrust band, BEP, hardware integrity). |
| [`visual4.md`](file:///x:/TAS/Agentic_project/visual4.md) | **Visual 4 Spec:** SHAP Feature Attribution Waterfall ($\phi_i$), Differential Diagnosis Matrix, and 4-tier Operator SOP. |
| [`visual_implementation_plan.md`](file:///x:/TAS/Agentic_project/visual_implementation_plan.md) | Master architectural blueprint for the reference registries, decoupled figure factory, and Tab 11 dashboard integration. |
| [`stage0_audit.md`](file:///x:/TAS/Agentic_project/stage0_audit.md) | Plain-English executive audit of the Stage 0 reference artifacts build. |
| [`REPOSITORY_STRUCTURE.md`](file:///x:/TAS/Agentic_project/REPOSITORY_STRUCTURE.md) | This document — authoritative repository and agent constitution guide. |

---

### Domain 2: `esp_agent/` — The Cognitive Multi-Agent Layer
Location: `x:/TAS/Agentic_project/esp_agent/`

The cognitive brain of the system. Rather than a single monolithic prompt, it employs a **hierarchical multi-agent team (Supervisor + Domain Specialists)** orchestrated with LangGraph.

#### Internal Constitution of `esp_agent`:

```
esp_agent/
├── src/
│   ├── agent/
│   │   ├── supervisor/               # 👑 Orchestration Layer
│   │   │   ├── graph.py              # LangGraph state graph definition & conditional edges
│   │   │   └── user_entry.py         # Entry router translating raw operator text to task state
│   │   │
│   │   ├── intent_router.py          # Fast semantic intent classification (OP01..OP07)
│   │   │
│   │   └── specialists/              # 🎯 Domain Specialist Subagents
│   │       ├── well_performance.py   # Specialist: ROR bounds, H-Q curves, head loss, flow rate
│   │       ├── fault_analyst.py      # Specialist: 13-fault signature matching, tipping points
│   │       ├── electrical_expert.py  # Specialist: VFD harmonics, voltage drop, insulation resistance
│   │       └── sop_operator.py       # Specialist: Field procedure lookup & safety interlocks
│   │
│   ├── adapters/                     # 🔌 Data Bridges (Common Backend Coupling)
│   │   ├── live_data_bridge.py       # Reads telemetry directly from labelled.db / unlabelled.db
│   │   └── asset_service.py          # O(1) asset metadata & equipment catalog cache
│   │
│   ├── services/                     # 🧠 Knowledge Retrieval
│   │   └── procedure_knowledge.py    # Matches diagnosed faults to engineering workovers & SOPs
│   │
│   └── events/                       # ⚡ Event Sourcing & Replay
│       ├── db_event_store.py         # Persistent incident event ledger
│       ├── processor.py              # Deduplication & alerting rules engine
│       └── replay_engine.py          # Replays asset event history for agent regression testing
│
├── knowledge_bases/                  # 📖 Authoritative Field Procedures & Objectives
│   └── esp/objectives/
│       ├── op01_current_status.json  # Schema for Well Health & Status queries
│       ├── op02_anomaly_triage.json  # Schema for Anomaly & Tipping Point analysis
│       ├── op03_hq_curve_check.json  # Schema for H-Q pump curve verification
│       └── op06_procedure_lookup.json# Schema for Field SOP & workover action lookups
│
└── tests/                            # 🧪 Agent Verification Suite
    ├── test_intent_routing_and_execution_tiers.py
    └── test_op01_vertical_slice.py
```

---

### Domain 3: `cced_esp/` — Shared Backend, Live Telemetry & React Client
Location: `x:/TAS/Agentic_project/cced_esp/`

This is the **operational production engine**. It owns database persistence, live MQTT collection, the 5-model ML pipeline, and the React frontend.

```
cced_esp/
├── backend/                          # 🚀 FastAPI Shared Backend (Port 8000)
│   ├── main.py                       # FastAPI app mounting all routers, CORS, and WebSocket manager
│   ├── config.py                     # Central configuration (DB paths, MQTT broker URL, limits)
│   ├── database.py                   # Primary SQLite time-series connection (WAL mode, connection pooling)
│   ├── database_ml.py                # Database connection for ground-truth feedback & model tracking
│   ├── database_normalized.py        # Database connection for normalized [0, 1] telemetry features
│   ├── mqtt_collector.py             # Live Paho MQTT subscriber with thread-safe queue & buffering
│   ├── transformer.py                # Raw MQTT payload -> standard database columns transformer
│   │
│   ├── api/                          # REST API Endpoints
│   │   ├── esp_routes.py             # Telemetry queries, active alarms, fleet health endpoints
│   │   ├── historian_routes.py       # Historical time-series queries by well and time window
│   │   └── replay_routes.py          # Historical scenario replay API (/api/esp/replay/control)
│   │
│   └── services/                     # Background Backend Services
│       ├── unified_pipeline.py       # Live 5-model inference pipeline (Anomaly -> Fault -> Risk -> RUL)
│       ├── vfd_diagnostic_service.py # Live bridge: incoming MQTT -> ESP_APM_models diagnostic card
│       ├── replay_service.py         # Mock/Replay engine (chronological telemetry playback)
│       └── decision_service.py       # Automated advisory and operational recommendation engine
│
├── data/                             # 💾 Telemetry Storage & Derived Reference Registries
│   ├── labelled.db                   # 3.89M rows, 73 wells, ground-truth labeled historical incidents
│   ├── unlabelled.db                 # 2.68M rows, continuous unlabelled historical telemetry
│   ├── normalized.db                 # Pre-normalized [0, 1] telemetry table (opg_normalized_telemetry)
│   │
│   └── artifacts/                    # 🎯 STAGE 0 DERIVED REFERENCE ARTIFACTS
│       ├── regime_baseline_registry.json # Clean P10-P90 normal envelopes binned by Hz for 28 wells
│       ├── fault_signature_library.json  # Empirical z-score deviation vectors for 10 fault types
│       └── build_manifest.json           # Provenance receipt (timestamp, row counts, source DB)
│
├── ml/                               # 🤖 Production Inference Models (The 5-Model Suite)
│   ├── models/
│   │   ├── anomaly_detector.py       # Multivariate Isolation Forest
│   │   ├── fault_classifier.py       # Hybrid rule + tree classifier for 13 faults
│   │   ├── risk_predictor.py         # Operational failure probability predictor
│   │   ├── rul_engine.py             # Remaining Useful Life (RUL) regression engine
│   │   └── rule_engine.py            # Physics-based heuristic safety limits engine
│   │
│   ├── explainability/
│   │   ├── explainer.py              # Root-cause feature attribution (SHAP-equivalent contributions)
│   │   └── templates.py              # Engineering natural-language advisory templates
│   │
│   └── learning/
│       ├── ground_truth_service.py   # Captures field operator feedback & links predictions to outcomes
│       └── continuous_trainer.py     # Background model retraining pipeline
│
├── scripts/                          # 🛠️ Maintenance & Offline Compilation Scripts
│   ├── build_reference_artifacts.py  # Stage 0 single-pass compiler for baselines & fault signatures
│   └── migrate_native_vfd_columns.py # DB schema migration script for native VFD telemetry columns
│
├── frontend-react/                   # 💻 Modern React Client (Vite + Tailwind + TypeScript)
│   ├── src/components/               # Subsystem equalizers, fleet maps, telemetry graphs
│   └── src/services/api.ts           # Connects to backend FastAPI REST endpoints and WebSockets
│
├── live_telemetry_cli.py             # Terminal live monitoring CLI (shows replayed/live feed in console)
├── mqtt_live_logger.py               # Raw MQTT topic listener and terminal logger
└── run_server.py                     # Entry point for backend server (uvicorn cced_esp.backend.main:app)
```

---

### Domain 4: `code/` — ML Research Engine, EDA Dashboard & Decoupled Figure Factory
Location: `x:/TAS/Agentic_project/code/`

The data-science laboratory and specialized Streamlit dashboard.

```
code/
├── eda/                              # 📊 Forensic Visualizations & ML Dashboard
│   ├── dashboard.py                  # 6,384-line 10-tab EDA and Diagnostic Dashboard
│   │                                 # (Target for Tab 11: "🎯 4-Visual Incident Forensics")
│   └── figure_factory.py             # ⭐ DECOUPLED FIGURE FACTORY (Pure Plotly go.Figure)
│                                     # Zero Streamlit coupling. Single source of truth for:
│                                     # • Visual 1: render_incident_tipping_timeline()
│                                     # • Visual 2: render_subsystem_equalizer() & pressure profile
│                                     # • Visual 3: render_hq_performance_curve()
│                                     # • Visual 4: render_shap_playbook_waterfall()
│                                     # Shared directly by dashboard.py and agent_streamlit.py!
│
├── models/                           # 🧠 Offline Diagnostic Engine & Heuristic Physics Models
│   ├── diagnostic_engine.py          # WellDiagnosticEngine (evaluates live telemetry snapshots)
│   ├── fault_classifier.py           # 14-fault physics rule classification engine
│   ├── anomaly_detector.py           # Isolation Forest anomaly scoring wrapper
│   ├── calibration_registry.py       # Legacy well calibration registry loader
│   ├── telemetry_adapter.py          # Maps 14 standard VFD sensor inputs
│   └── test_fault_scenarios.py       # Unit test fixtures for 13 fault modes
│
├── pipeline/                         # Data Normalization Pipelines
│   └── build_normalized_db.py        # Generates normalized.db from raw telemetry
│
└── tests/
    └── test_figure_factory_forensics.py # Pytest verification suite for forensic figures
```

---

### Domain 5: `esp-knowledge/` & `archive/` — Domain Corpus & Deprecated Code
* **`esp-knowledge/`**: Contains raw API standards (API RP 11S1, 11S4, 11S8), Takacs TDH manuals, Baker Hughes/Weatherford catalogs, and Docling parsed JSONs used by the RAG procedure knowledge service.
* **`archive/`**: Contains zipped deprecated sandboxes (`ccep_deprecated.zip`, `deprecated_ml_telemetry_api_v1.zip`). All loose duplicates have been cleaned up.

---

## 4. The Shared Backend: React vs. Streamlit Agent

### Is the Backend Common to Both?
**YES, 100% ABSOLUTELY.** Both agents query the exact same physical system and data assets:

```
                               ┌──────────────────────────────────────────────┐
                               │             SHARED BACKEND LAYER             │
                               │                                              │
                               │  FastAPI (cced_esp/backend/main.py :8000)    │
                               │  SQLite: labelled.db, unlabelled.db          │
                               │  Artifacts: data/artifacts/*.json            │
                               │  Inference: cced_esp/ml/ unified_pipeline    │
                               └──────────────┬────────────────┬──────────────┘
                                              │                │
                        HTTP REST / WebSockets│                │Direct Python Imports
                                              ▼                ▼
                            ┌─────────────────────┐   ┌─────────────────────────────┐
                            │ REACT FRONTEND AGENT│   │  STREAMLIT AGENT INTERFACE  │
                            │ (frontend-react/)   │   │  (agent_streamlit.py)       │
                            │                     │   │                             │
                            │ • Client-side UI    │   │ • Python-native chat        │
                            │ • Uses fetch() to   │   │ • Imports esp_agent graph   │
                            │   /api/esp/...      │   │ • Imports figure_factory    │
                            │ • Listens to WS     │   │ • Renders Plotly 4-visual   │
                            │   /ws/telemetry     │   │   suite inline in chat      │
                            └─────────────────────┘   └─────────────────────────────┘
```

1. **React-based Frontend Agent:**
   - Consumes the backend remotely over network protocols:
     - **REST Endpoints:** `GET /api/esp/wells`, `GET /api/esp/telemetry/live`, `POST /api/esp/replay/control`.
     - **WebSocket:** `ws://localhost:8000/ws/telemetry` receives real-time JSON packets (`ESP_REPLAY_UPDATE` or `LIVE_TELEMETRY`).
   - Ideal for operations control-room displays and web browser clients.

2. **Streamlit-based Agent (`agent_streamlit.py`):**
   - Runs in the same Python runtime as the server or agent engine.
   - Calls `esp_agent.src.agent.supervisor.graph` directly in-process for low-latency conversational reasoning.
   - Directly calls `code/eda/figure_factory.py` to render interactive Plotly figures (`st.plotly_chart`) directly inside chat bubbles when the operator asks: *"Show me why FSWS-003 tripped."*
   - Ideal for field engineers, diagnostic deep-dives, and ad-hoc chat investigations.

---

## 5. Summary Checklist of Workspace Cleanliness

* [x] No duplicate zip archives in working directories (removed `code/models (2).zip`).
* [x] Temporary test CSV export dumps ignored in `.gitignore` (`data/*.csv`, `data/scenarios/`).
* [x] All 4 visual specs documented in root: `visual1.md`, `visual2.md`, `visual3.md`, `visual4.md`.
* [x] Master implementation roadmap in root: `visual_implementation_plan.md`.
* [x] Stage 0 reference artifacts generated and locked: `cced_esp/data/artifacts/`.
* [x] Zero Streamlit coupling in `figure_factory.py` (guarantees seamless agent figure rendering).
