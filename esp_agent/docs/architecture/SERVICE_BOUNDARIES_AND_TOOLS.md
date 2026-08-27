# Sprint 1.4 — Service Boundaries, Contracts & Tool Inventory

> **Phase 1 Deliverable:** Service & Tool Contract Definitions  
> **Grounded in:** `Guidelines.pdf` Appendix B & `ESP_Agentic_Assistant_Architecture_Detailed_Design_UPDATED_Guideline_Mapped.docx` §4, §6  
> **Date:** 2026-08-25  

---

## 1. Logical Service Inventory & Boundaries

| Service Name | Primary Purpose | Owner | Transport | Timeout | Error Fallback |
|---|---|---|---|---|---|
| **Asset Context Service** | Asset metadata, installation, pump/motor ratings | Advait | REST (`GET /assets/{id}`) | 2000ms | Local DB cache projection |
| **Telemetry Service** | Live/historical time-series, data quality | Simulator / Advait | REST / WS | 3000ms | Disclose STALE status |
| **Model Adapter Service** | Standardized interface over 4 ESP ML models | ESP ML Team | REST / gRPC | 3000ms | Disclose missing model prediction |
| **Engineering Service** | Deterministic calculations (TDH, ΔP, ROR margin) | Engineering | Python / REST | 1000ms | Disclose calculation assumption |
| **Knowledge Service** | Multi-tier retrieval (Exact, SQL, pgvector, BM25) | Agent Team | Python / REST | 2000ms | Local vector fallback |
| **Case / History Service** | Past teardowns, RCAs, historical similarity | Knowledge Eng | REST / SQL | 3000ms | Empty case list |
| **Audit Service** | Persists run traces, tool inputs, evidence packs | Agent Team | PostgreSQL / OT | Async | Background log queue |

---

## 2. Typed Agent Tool Inventory (Guidelines.pdf Appendix B)

```python
# Asset Tools
get_asset_context(asset_id: str) -> AssetContextPayload
get_asset_list(filter: Optional[str]) -> List[AssetSummaryPayload]

# Telemetry Tools
get_live_snapshot(asset_id: str) -> TelemetryPayload
get_history_window(asset_id: str, start_time: str, end_time: str, signals: List[str]) -> TimeSeriesPayload

# Model Adapter Tools
get_rule_status(asset_id: str) -> RuleStatusPayload
get_anomaly_result(asset_id: str) -> AnomalyResultPayload
get_failure_prediction(asset_id: str) -> FailurePredictionPayload
get_fault_diagnosis(asset_id: str) -> FaultDiagnosisPayload
get_health_index(asset_id: str) -> HealthIndexPayload

# Engineering Tools
calculate_operating_point(asset_id: str, flow: float, pip: float, pdp: float) -> OperatingPointPayload
calculate_tdh(asset_id: str, pdp: float, pip: float, fluid_sg: float) -> CalculationPayload

# Knowledge Tools
search_knowledge_base(query: str, tenant_id: str, top_k: int = 5) -> List[KnowledgeEvidence]
search_fault_knowledge(pattern: Dict[str, Any]) -> List[FaultPatternPayload]
get_term_definition(term: str) -> GlossaryPayload

# Audit Tools
record_advisory(advisory: AdvisoryPayload) -> AuditRecordPayload
```

---

## 3. Communication Protocols

- **Agent ↔ Backend Services:** REST/HTTPS (JSON payload over FastAPI).
- **Agent ↔ Database:** asyncpg / SQLAlchemy over PostgreSQL TCP `5432`.
- **Agent ↔ LLM Service:** OpenAI-compatible REST API (vLLM / Ollama endpoint).
- **Frontend ↔ Agent API:** HTTPS REST for queries (`POST /diagnose`); Server-Sent Events (SSE) or WebSockets for response streaming.
