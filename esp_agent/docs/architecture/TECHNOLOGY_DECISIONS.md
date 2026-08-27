# Sprint 1.5 — Technology & Deployment Decisions

> **Phase 1 Deliverable:** Technology Stack & Deployment Freeze  
> **Grounded in:** `Guidelines.pdf` §5.3, §10 & `ESP_Agentic_Assistant_Architecture_Detailed_Design_UPDATED_Guideline_Mapped.docx` §15  
> **Date:** 2026-08-25  

---

## 1. Frozen Technology Stack

| Layer | Technology Choice | Classification | Justification |
|---|---|---|---|
| **Agent Framework** | Python 3.10+ & LangGraph | Implementation Recommendation | Stateful multi-step graph execution & objective routing |
| **API Framework** | FastAPI | Implementation Recommendation | Asynchronous OpenAPI gateway with high performance |
| **Data Validation** | Pydantic v2 | Guideline-Aligned | Strict schema enforcement for contracts & EvidencePack |
| **Primary Database** | PostgreSQL 16 | Implementation Recommendation | Relational storage for metadata, audit, faults, and objectives |
| **Vector Index** | `pgvector` extension | Implementation Recommendation | Integrated 768-dim cosine similarity search (`knowledge_embeddings`) |
| **Embedding Model** | `all-mpnet-base-v2` | Guideline-Aligned | High-fidelity local offline semantic embeddings |
| **Document Parser** | Docling (PyMuPDF fallback) | Implementation Recommendation | Structure-aware extraction (tables, headings, page numbers) |
| **LLM Runtime** | vLLM / Ollama (OpenAI API format) | Guideline-Aligned (§5.3) | Local high-throughput inference with zero cloud dependency |
| **Cache & State** | Redis | Implementation Recommendation | Session state, rate limiting, event stream caching |

---

## 2. Deployment Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│ DOCKER CONTAINER: esp_agent_platform                            │
│                                                                 │
│  ├── FastAPI App Gateway (`src/api/main.py`)                   │
│  ├── LangGraph Supervisor (`src/agent/runtime.py`)             │
│  ├── Tool Registry (`src/tools/registry.py`)                   │
│  ├── Hybrid Retrieval (`src/services/retrieval_service.py`)    │
│  └── Context Builder (`src/services/context_builder.py`)        │
└────────────────────────────────┬────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ CONTAINER:       │    │ CONTAINER:       │    │ CONTAINER:       │
│ postgres:16-pgvector  │ local_llm_runtime│    │ redis:7-alpine   │
│ DB: esp_agent    │    │ vLLM / Ollama    │    │ Session / Cache  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```
