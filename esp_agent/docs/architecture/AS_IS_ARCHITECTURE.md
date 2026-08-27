# Sprint 1.1 — As-Is Architecture & Repository Inventory

> **Phase 1 Deliverable:** Sprint 1.1 Current-State Audit  
> **Repository Target:** `x:\TAS\Agentic_project\esp_agent`  
> **Date:** 2026-08-25  

---

## 1. Executive Summary

This document captures the current-state inventory, runtime discovery, existing tools, KB setup, hardcode register, and component reusability assessment of the `esp_agent` codebase prior to Phase 2 contract & service integration.

---

## 2. Component Inventory

```text
x:\TAS\Agentic_project\esp_agent
 ├── src/
 │    ├── adapters/
 │    │    ├── docling_parser.py    [WORKING] Docling layout parser wrapper
 │    │    ├── graph.py             [WORKING] Component topology graph (NetworkX)
 │    │    ├── rag.py               [WORKING] RAG adapter (pgvector + local search fallback)
 │    │    ├── rules.py             [WORKING] 9 threshold rule evaluation engine
 │    │    └── telemetry.py         [WORKING] Telemetry adapter (CSV fallback)
 │    ├── agent/
 │    │    ├── runtime.py           [WORKING/PARTIAL] LangGraph 6-node diagnostic DAG
 │    │    └── state.py             [WORKING] Pydantic diagnostic state
 │    ├── api/
 │    │    └── main.py              [WORKING] FastAPI server (/health, /diagnose)
 │    ├── schemas/
 │    │    ├── canonical.py         [WORKING] Canonical Pydantic schemas
 │    │    └── evidence.py          [WORKING] Pydantic EvidencePack & Evidence schemas
 │    ├── services/
 │    │    ├── context_builder.py   [WORKING] ContextBuilder & zero-hallucination prompt overlay
 │    │    └── retrieval_service.py [WORKING] Hybrid retrieval service (YAML + SQL + pgvector)
 │    └── tools/
 │         ├── evaluate_rules.py    [WORKING] Tool wrapper for rule engine
 │         ├── fetch_telemetry.py   [WORKING] Tool wrapper for telemetry adapter
 │         ├── generate_chart.py    [WORKING] Tool wrapper for matplotlib charts
 │         ├── query_topology.py    [WORKING] Tool wrapper for graph adapter
 │         └── search_docs.py       [WORKING] Tool wrapper for RAG adapter
 ├── scripts/
 │    ├── init_db.py                [WORKING] PostgreSQL 9-table schema initialization
 │    ├── seed_db.py                [WORKING] Seeding manifests, faults, glossary, objectives
 │    └── chunk_and_embed.py        [WORKING] Chunking & pgvector embedding pipeline
 └── tests/                         [WORKING] 21 unit & integration tests (100% pass)
```

---

## 3. Component Classification & Reuse Register

| Component | Status | Recommendation | Notes |
|---|---|---|---|
| `src/adapters/docling_parser.py` | ✅ WORKING | **KEEP** | Standardized PDF layout parser; processed 19 PDFs into 243 tables |
| `src/adapters/graph.py` | ✅ WORKING | **KEEP** | Handles ESP component topology for local well pads |
| `src/adapters/rag.py` | ✅ WORKING | **REFACTOR** | Upgrade to query `retrieval_service.py` directly |
| `src/adapters/rules.py` | ✅ WORKING | **KEEP** | Evaluates 9 operational threshold rules |
| `src/adapters/telemetry.py` | 🟡 PARTIAL | **REFACTOR** | Add live REST API mode (`GET /telemetry/live`) while keeping CSV fallback |
| `src/services/retrieval_service.py` | ✅ WORKING | **KEEP** | Handles exact glossary lookups, SQL table search, pgvector similarity, and conflict detection |
| `src/services/context_builder.py` | ✅ WORKING | **KEEP** | Assembles zero-hallucination EvidencePack and prompt overlays with data freshness |
| `src/schemas/evidence.py` | ✅ WORKING | **KEEP** | Pydantic v2 schemas for evidence pack and source citations |
| `src/agent/runtime.py` | 🟡 PARTIAL | **REFACTOR** | Currently a 6-node fixed LangGraph DAG. Needs Objective Router & LLM client wiring |
| `src/api/main.py` | ✅ WORKING | **KEEP** | FastAPI REST entrypoint |

---

## 4. Hardcode & Demo Logic Register

| Location | Hardcoded Item | Plan for Phase 2 Replacement |
|---|---|---|
| `context_builder.py` | `{"installed_pump": "ESP-Well-001"}` stub asset | Replace with `AssetService.get_asset(asset_id)` |
| `runtime.py` | Static text template in `synthesize_diagnosis` node | Replace with `LLMClient` + `ContextBuilder` prompt overlay |
| `telemetry.py` | Loads `data/sample_telemetry.csv` by default | Add `LiveTelemetryAdapter` with HTTP client + CSV fallback |
| `seed_objectives.yaml` | Only 4 MVP objectives seeded | Expand to all 18 operational categories (§5.2) |

---

## 5. Technical Debt Register

1. **BM25 & Reranker Missing:** Vector search uses cosine similarity only. `rank_bm25` and cross-encoder reranker need integration in `retrieval_service.py`.
2. **LLM Connection Unwired:** The `ContextBuilder` formats a structured prompt overlay, but it is not yet dispatched to a local LLM (vLLM / Ollama) or API client.
3. **Model Adapter Missing:** The 4 external AI models (Rule Engine, Anomaly, Failure Prediction, Fault Classifier) do not have a dedicated adapter file (`model_adapter.py`).
