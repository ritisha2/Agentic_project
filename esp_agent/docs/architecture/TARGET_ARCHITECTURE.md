# Sprint 1.2 — Target Architecture Definition

> **Phase 1 Deliverable:** Target Architecture Freeze  
> **Grounded in:** `Guidelines.pdf` §4.1, §13.1 & `ESP_Agentic_Assistant_Architecture_Detailed_Design_UPDATED_Guideline_Mapped.docx`  
> **Date:** 2026-08-25  

---

## 1. Top-Level 9-Layer Target Architecture

```text
┌───────────────────────────────────────────────────────────────────────┐
│ 1. EXPERIENCE LAYER                                                   │
│    Operator Dashboard • Chat Interface • Evidence Cards • UI Context │
└──────────────────────────────┬────────────────────────────────────────┘
                               │ HTTPS / WebSockets / SSE
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│ 2. AGENT API GATEWAY (`src/api/main.py`)                              │
│    FastAPI Gateway • Auth/RBAC • Session State • Response Streaming   │
└──────────────────────────────┬────────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│ 3. SUPERVISOR AGENT (`src/agent/runtime.py`)                          │
│    LangGraph Orchestrator • Intent Classification • Objective Router  │
└──────────────────────────────┬────────────────────────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ 4. OBJECTIVE     │  │ 5. TOOL REGISTRY │  │ 6. POLICY /      │
│    ROUTER        │  │    & ACL GATE    │  │    SAFETY GATE   │
│ 18 Categories    │  │ Least-Privilege  │  │ Constraints      │
└─────────┬────────┘  └────────┬─────────┘  └────────┬─────────┘
          │                    │                     │
          └────────────────────┼─────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│ 7. SERVICE INTEGRATION LAYER (`src/adapters/` & `src/services/`)     │
│    Asset Context • Telemetry • Engineering • Knowledge • Model Adapter│
└──────────────────────────────┬────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ 8. EVIDENCE PACK │  │ CONTEXT BUILDER  │  │ 9. LLM REASONING │
│ Provenance & QoD │  │ Prompt Overlay   │  │ vLLM / Local API │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 2. Specialist Agents Breakdown (Sprint 1.2 Task 3)

The Supervisor Agent orchestrates 5 logical specialist subgraphs:

| Specialist Agent | Core Responsibility | Input Services | Allowed Tools | Primary KB Sources |
|---|---|---|---|---|
| **Well Performance Agent** | Operating point, hydraulic balance, TDH calculation, BEP deviation, ROR margin | Telemetry, Engineering Service | `calculate_tdh`, `calculate_operating_point`, `get_history_window` | Pump Curves, OEM Datasheets, Physics Equations |
| **Reliability Agent** | Motor thermal limits, vibration analysis, degradation trends, RUL assessment | Model Adapter, Telemetry Service | `get_anomaly_result`, `get_failure_prediction`, `get_rule_status` | Fault Taxonomy, Run-Life Studies, RCA Reports |
| **Knowledge Agent** | Manual lookups, exact terminology definitions, client SOP procedures, API standards | Knowledge Service | `search_knowledge_base`, `search_fault_knowledge`, `get_term_definition` | OEM Manuals, Client SOPs, API/IEC Standards |
| **Optimization / Digital Twin Agent** | Frequency what-if simulation, production vs risk trade-offs | Digital Twin Service, Engineering | `run_what_if_frequency`, `calculate_ror_margin` | Envelope Limits, Hydraulic Models |
| **Maintenance Agent** | Repair history, teardown logs, intervention planning, parts lookup | Case/Maintenance Service | `get_maintenance_history`, `search_similar_case` | Workover Reports, Teardown Logs, CMMS |

---

## 3. Deployment Granularity

```text
[ SINGLE DEPLOYABLE AGENT PLATFORM CONTAINER ]
  ├── FastAPI Gateway (`src/api/main.py`)
  ├── LangGraph Supervisor Engine (`src/agent/runtime.py`)
  ├── Specialist Subgraphs (Logical routing inside LangGraph)
  ├── Tool Registry & ACL Gate (`src/tools/registry.py`)
  ├── Hybrid Retrieval Service (`src/services/retrieval_service.py`)
  └── Evidence & Context Builder (`src/services/context_builder.py`)
  
[ EXTERNAL INFRASTRUCTURE CONTAINERS ]
  ├── PostgreSQL 16 + pgvector (Structured DB + Embeddings)
  ├── Local LLM Server (vLLM / Ollama OpenAI-compatible endpoint)
  └── Redis (Session state & Event stream cache)
```

> **Implementation Rule:** Logical specialist agents are implemented as modular Python subgraphs within a single deployable container, avoiding unnecessary microservice overhead for MVP delivery.
