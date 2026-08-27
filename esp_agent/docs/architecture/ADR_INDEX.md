# Sprint 1.6 — Architecture Decision Records (ADRs) & Guideline Traceability

> **Phase 1 Deliverable:** ADR Index & Guideline Traceability Matrix  
> **Date:** 2026-08-25  

---

## 1. Architecture Decision Records (ADR Index)

### ADR-001: Separation of Analytical Models and Agentic Reasoning Layer
- **Status:** APPROVED
- **Context:** The ESP AI Model Team builds Rule Engine, Anomaly Detection, Failure Prediction/RUL, and Fault Classification models.
- **Decision:** The Agentic layer will NEVER execute model algorithms or retrain models internally. It consumes model outputs via `ModelAdapter` as structured evidence.
- **Consequence:** Clean scope boundary; model team updates do not break Agent code.

### ADR-002: Use PostgreSQL + pgvector for Initial Vector Store
- **Status:** APPROVED
- **Context:** Need vector similarity search alongside relational metadata (fault patterns, glossary, objectives).
- **Decision:** Use PostgreSQL 16 with `pgvector` enabled rather than a separate vector DB container (Qdrant) for MVP.
- **Consequence:** Simplified infrastructure operations; single database for structured & vector data.

### ADR-003: Single Deployable Container for Agent Platform
- **Status:** APPROVED
- **Context:** Guidelines.pdf defines 5 logical specialist agents (Well Performance, Reliability, Knowledge, Optimization, Maintenance).
- **Decision:** Specialist agents will be implemented as modular Python subgraphs inside a single LangGraph application container.
- **Consequence:** Eliminates inter-container network latency and complex RPC deployment for MVP.

### ADR-004: OpenAI-Compatible Local LLM Abstraction
- **Status:** APPROVED
- **Context:** Local high-throughput LLM inference is required by Guidelines.pdf §5.3.
- **Decision:** Abstract LLM access via an OpenAI-compatible REST API client (`vLLM` / `Ollama`).
- **Consequence:** Easy switching between local models (Qwen, Llama 3.1, Mistral) and cloud fallback APIs without changing agent logic.

---

## 2. Guideline Traceability Matrix

| Guidelines.pdf Section | Architecture Requirement | Implementation File / Status | Classification |
|---|---|---|---|
| **§1.3 (p.5)** | No direct autonomous writes in initial releases | Enforced by Tool Registry (read-only default) | GUIDELINE REQUIREMENT |
| **§3.1 (p.6)** | Evidence Precedence Hierarchy (A–F priority) | Implemented in `retrieval_service.py` & `evidence.py` | GUIDELINE REQUIREMENT |
| **§4.1 (p.7)** | 9 Architectural Layers | Documented in `docs/TARGET_ARCHITECTURE.md` | GUIDELINE REQUIREMENT |
| **§5.3 (p.8)** | Local high-throughput LLM inference (vLLM/SGLang) | Configured in `docs/TECHNOLOGY_DECISIONS.md` | GUIDELINE REQUIREMENT |
| **§10.1 (p.14)** | Complete KB domain taxonomy (OEM, Physics, SOPs, Curves) | Seeded in `esp-knowledge/deterministic/` | GUIDELINE REQUIREMENT |
| **§10.2 (p.15)** | Hybrid Retrieval (Exact + Vector + BM25) | Implemented in `src/services/retrieval_service.py` | GUIDELINE REQUIREMENT |
| **§11 (p.21)** | Independent versioned ML Services | Wrapped by `src/adapters/model_adapter.py` | GUIDELINE REQUIREMENT |
| **§13.1 (p.24)** | Supervisor & Specialist Agents organization | LangGraph subgraphs in `src/agent/runtime.py` | IMPLEMENTATION CHOICE |
| **§22.1 (p.30)** | 9-step Mandatory Question-Handling Method | Implemented in `src/agent/objective_router.py` | GUIDELINE REQUIREMENT |
| **Appendix B (p.30)** | Typed Tool Service Contracts with units/timestamps | Implemented in `src/schemas/contracts.py` | GUIDELINE REQUIREMENT |
| **Appendix C (p.31)** | Standard Advisory Response schema | Implemented in `src/schemas/advisory.py` | GUIDELINE REQUIREMENT |

---

## 3. Phase 1 Exit Gate Verification

- [x] **WHO owns what?** → Defined in `SCOPE_BOUNDARY_RACI.md`
- [x] **WHERE does data come from?** → Defined in `SERVICE_BOUNDARIES_AND_TOOLS.md`
- [x] **WHO calls whom?** → Defined in `TARGET_ARCHITECTURE.md`
- [x] **WHAT is a tool vs service?** → Defined in `SERVICE_BOUNDARIES_AND_TOOLS.md`
- [x] **WHAT does the Agent see?** → Defined in `AS_IS_ARCHITECTURE.md` & `contracts.py`
- [x] **HOW do components communicate?** → Defined in `SERVICE_BOUNDARIES_AND_TOOLS.md`
- [x] **WHAT is mandatory from Guidelines.pdf?** → Documented in Guideline Traceability Matrix above.

**PHASE 1 IS OFFICIALLY FROZEN & COMPLETE.**
