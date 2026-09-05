# Agent Jane — Core Agentic Architecture

> Ground-truth document. Generated from live code reading of `esp_agent/src/agent/supervisor/graph.py`, `user_entry.py`, `agent_streamlit.py`, and `intent_router.py` on the `fe` branch (HEAD `8cf4bf1`).

---

## 0. One-line summary

```
User query
  → intent router (classify → tier → ambiguity check)
  → LangGraph StateGraph (14 nodes, tier-gated data loading, specialist loop)
  → evidence pack (ranked, frozen)
  → LLM synthesis (Qwen 3B, json_mode, local)
  → StandardAdvisoryPayload
  → Streamlit renders progressive disclosure
```

---

## 1. Entry point — `agent_streamlit.py → execute_agent_query()`

```
agent_streamlit.py
└─ execute_agent_query(query, well_id, session_id)
     ├─ BackendCircuitBreaker.allow_request()       # skip if backend dead
     ├─ UserEntryAdapter.run(query, asset, session)  # in-process call (NOT HTTP)
     │    └─ ConversationStore.get_last_well()       # Redis/fallback, implicit well resolution
     │    └─ ConversationStore.get_history(limit=10) # recent_turns for context
     │    └─ intent_router.route(query, conv_ctx)    # see §2
     │    └─ create_initial_agent_state(...)
     │    └─ supervisor_graph.invoke(state, config={thread_id})
     │    └─ handle __interrupt__ → ClarificationNeeded
     │    └─ return StandardAdvisoryPayload
     └─ on ClarificationNeeded → show well chips → UserEntryAdapter.resume(thread_id, answer)
```

**Key facts:**
- Streamlit calls `UserEntryAdapter` **in-process** — no HTTP to the BFF (`/api/ui/agent/stream`). This is the current architecture gap vs the React UI.
- `thread_id = session_id or request_id` — stable key per session. Enables LangGraph's RedisCheckpointer to save/restore state across turns and support `interrupt()`/`Command(resume=...)` HITL.
- Implicit well: if query has no well name and session memory has one, `get_last_well()` fills it automatically.

---

## 2. Intent router — `IntentRouter.route()`

**File:** `esp_agent/src/agent/intent_router.py`

```
query + conversation_context (last_well, last_objective, recent_turns)
  │
  ├─ 1. Follow-up carry-forward (exact match ~14 phrases: "why", "explain"...)
  │       → reuse last_objective, conf=0.90, path=Path_A_FollowUp
  │
  ├─ 2. SCADA/MQTT event code (Path C)
  │       → direct YAML mapping → objective, conf=1.0
  │
  ├─ 3. Greeting/small-talk bucket (Path A)
  │       → collapses "hiiiii"→"hi", exact set match → OP07_GENERAL_INQUIRY, conf=0.98
  │
  ├─ 4. Deterministic keyword (Path A)
  │       → word-boundary regex against all objective intent_classes
  │       → specificity-sorted, priority: safety(100) > fleet-match(20) > single(15) > mismatch(1)
  │       → first hit wins, conf=0.95–0.96
  │
  ├─ 5. Semantic token overlap (Path B)
  │       → tokenize query − 45-word stopword set
  │       → score overlap vs each objective title(×0.2) + description(×0.1)
  │       → scope tie-breaker (fleet/single)
  │       → semantic_confidence = min(0.85, 0.5 + best_score)
  │       → ⚠️ KNOWN BUG: seed default is OP03_FAULT_DIAGNOSIS (→ Plan.md Phase 2.0)
  │
  ├─ 6. LLM classifier fallback (Path LLM)  ← only when semantic_confidence < 0.78
  │       → Qwen 3B, max_tokens=20, temp=0.0, picks one objective_id
  │
  └─ Ambiguity gate: confidence < 0.65 AND no well anchored → is_ambiguous=True
```

**Returns:** `RouteResult(objective_id, confidence, path, is_ambiguous)`

---

## 3. Objective spectrum — OP00 to OP14

| ID | Title | Tier | Specialists | Notes |
|---|---|---|---|---|
| OP00 | Operational Control | T0_SAFETY_REFUSAL | none | Hard refusal, no data load, instant |
| OP01 | Current Status | T2_SNAPSHOT | well_performance | Telemetry + engineering only |
| OP02 | Production Decline RCA | T3_FULL_DIAGNOSTIC | well_performance, reliability | Full pipeline |
| OP03 | Fault Diagnosis | T3_FULL_DIAGNOSTIC | reliability, knowledge | Full pipeline |
| OP04 | Health Assessment / RUL | T3_FULL_DIAGNOSTIC | reliability | Full pipeline |
| OP05 | Early Warning | T3_FULL_DIAGNOSTIC | reliability | Full pipeline |
| OP06 | SOP / Procedure Lookup | T1_KB_ONLY | knowledge | KB only, no telemetry/model |
| OP07 | General Inquiry | T1_DIRECT_LLM | none | Bypasses pipeline entirely, pure LLM |
| OP08–OP13 | Fleet (Inventory/Opt/Design/Maint/Cases/Exec) | T_FLEET | none | Map-reduce fleet node |
| OP14 | Operational History | T4_HISTORY | none | Reads unlabelled.db window |

---

## 4. LangGraph supervisor graph — node-by-node

```
START
  │
  ▼
[1] resolve_objective_node
      IntentRouter.route() → obj_id, tier, is_ambiguous
      ──────────────────────────────────────────
      conditional branch:
        OP00         →  [control_refusal]  → END
        fleet scope  →  [fleet_inventory]  → END
        is_ambiguous →  [clarification]    → [resolve_asset] (after resume)
        OP07         →  [general_inquiry]  → END
        else         →  [resolve_asset]
  │
  ▼
[2] resolve_asset_node
      AssetService.get_asset(asset_id)
      → ctx["asset"] = {type, pump_model, ...}
  │
  ▼
[3] data_quality_gate_node
      Tier gate:
        T1_KB_ONLY / T1_DIRECT_LLM  → ctx["telemetry"] = {}  (skip)
        T4_HISTORY                  → ctx["telemetry"] = {}  (deferred to historian)
        T2 / T3                     → TelemetryService.get_latest()
                                      + live_bridge.get_telemetry_as_agent_dict()
                                      + DataQualityGate.evaluate()
                                      + verify_telemetry() → provenance tag (LIVE/FALLBACK/DEGRADED)
  │
  ▼
[4] load_minimum_context_node
      Tier gate:
        T1_KB_ONLY  → procedure_knowledge_service.lookup_limits()
        T4_HISTORY  → history_analytics.fetch_history_dataframe()
                      history_analytics.compute_operational_metrics()
                      history_analytics.compute_baseline_deviations()
        T2_SNAPSHOT → LiveDataBridge.get_engineering_context()
        T3_FULL     → MCPToolClient.invoke("get_model_output")   (legacy health-index)
                      live_bridge.get_vfd_diagnostic()           (14-signal VFD engine)
                      MCPToolClient.invoke("calculate_tdh")
                      LiveDataBridge.get_engineering_context()
                      history_analytics.fetch_history_dataframe() (baseline deviations)
                    → ctx["models"], ctx["vfd_diagnostic"], ctx["engineering"],
                      ctx["history_analytics"]
  │
  ▼
[5] plan_node
      ObjectiveDefinition.allowed_specialists → plan["steps"] = ["reliability", "knowledge", ...]
      (OP07 → [], OP14 → [] — no specialists for these tiers)
  │
  ▼
[6] delegate_node  ←──────────────────────────────────┐
      PolicyEngine.enforce_specialist_rbac()           │
      dispatch to active specialist                    │
  │                                                    │
  ▼                                                    │
[7] collect_results_node                               │
      Run specialist subgraph (LangGraph graph per specialist):
        "well_performance" → well_performance_graph
        "reliability"      → reliability_graph
        "knowledge"        → knowledge_graph
        "digital_twin"     → digital_twin_graph
        "maintenance"      → maintenance_graph
        "engineering"      → EngineeringSpecialist.analyze()
      → specialist_results[], evidence_refs[]
      → plan["active_step"] += 1
      conditional: more steps? → [delegate]  else → [evidence_gate]
  │
  ▼
[8] evidence_gate_node
      ContextBuilder.build_evidence_pack(
          asset_context, telemetry, model_outputs, vfd_diagnostic,
          engineering, knowledge_results, specialist_results
      )
      → EvidencePack (22-field EvidenceItem × N, authority-ranked A–F, frozen SHA-256)
      → EvidenceRepository.save_evidence_pack()
      → evidence_refs[] merged with pack.items
  │
  ▼
[9] conflict_check_node
      detect contradictions between specialist outputs
  │
  ▼
[10] safety_gate_node
       advisory_only = obj_def.safety.advisory_only
       blocked_actions list
  │
  ▼
[11] generate_advisory_draft_node
       Tier-specific synthesis:
         OP06 → procedure_knowledge_service.format_advisory_text()
                + optional LLM grounding
         OP01 → deterministic telemetry snapshot (no LLM)
         OP14 → deterministic history metrics (no LLM)
         T3   → CompactContextBuilder.build_from_agent_state()
                + LLMAdapter.generate_advisory_from_compact_context()
                  (Qwen 3B, json_mode=True, json-repair loop)
                  → AdvisoryOutputSchema {assessment, hypotheses[], uncertainties, recommendation, verification}
                + evidence priority carve-out (VFD/ML refs guaranteed a seat in cap-8 list)
                + trend_desc from VFD dynamics
                + deviations_list (expected vs actual)
                + ranked_hypotheses[] (from LLM or VFD fallback)
                + follow_up_prompts[]
       → StandardAdvisoryPayload (full contract: see §5)
       → CheckpointManager.save_checkpoint() to Redis
  │
  ▼
  END
```

---

## 5. Output contract — `StandardAdvisoryPayload`

```python
StandardAdvisoryPayload:
  advisory_id            # ADV-{run_id}
  asset_id               # well / FLEET / SYSTEM
  objective_id           # OP01–OP14
  timestamp              # ISO UTC

  assessment             # narrative: what is observed
  evidence[]             # AdvisoryEvidenceItem × ≤8 (priority: VFD/ML first)
                         #   source_type, source_id, observation, source_deep_link
  diagnosis              # root cause / hypothesis top-1
  confidence             # 0.0 – 1.0
  risk                   # horizon string
  recommendation         # bounded operational action
  expected_impact        # production / reliability impact
  constraints[]          # safety / forbidden actions
  verification[]         # step-by-step human checks
  provenance[]           # LLM engine: ONLINE/OFFLINE, telemetry_source: LIVE/FALLBACK, run ID

  # Phase 4 extended fields
  trend                  # "Thermal slope: ±°C/hr | ΔP: PSI | Torque proxy: A/Hz"
  expected_vs_actual[]   # parameter corridor deviations [{parameter, current, nominal, status}]
  ranked_hypotheses[]    # [{cause, confidence, reasoning, supporting_evidence[]}]
  follow_up_prompts[]    # suggested next queries surfaced to operator
```

Evidence authority levels:
- `LEVEL_A` Installed/approved specs
- `LEVEL_B` OEM manuals
- `LEVEL_C` Customer engineering calculations
- `LEVEL_D` Site SCADA history / live VFD engine
- `LEVEL_E` Industry standard
- `LEVEL_F` LLM prior

---

## 6. Short-circuit paths (no specialist pipeline)

| Path | Trigger | What runs |
|---|---|---|
| Safety refusal | OP00 | Deterministic text, no data, instant `→ END` |
| Fleet map-reduce | OP08–13 | `fleet_inventory_node`, no single-asset pipeline |
| Conversational | OP07 / greeting | `general_inquiry_node`: one LLM chat call, no data load |
| HITL clarification | `is_ambiguous=True` | `interrupt()` pauses graph, streams question, `Command(resume)` continues to `resolve_asset` |

---

## 7. Memory & persistence

| Layer | Implementation | Key | TTL |
|---|---|---|---|
| Conversation turns | `ConversationStore` (Redis + in-memory fallback) | `esp:conv:{session_id}` | 7 days, last 20 turns |
| LangGraph state/interrupt | `RedisCheckpointer` (subclasses `MemorySaver`) | `esp:lg_check:{thread_id}` | Redis TTL |
| Per-well episodic | `WellEpisodicMemoryStore` | per asset_id | in-memory |
| Evidence pack | `EvidenceRepository` | in-memory + Redis | per-run |
| VFD diagnosis cache | `VFDDiagnosticService._latest_by_well` | in-memory, pre-warmed 50 wells at startup | live |

---

## 8. Data sources by tier

```
T0  (OP00)  ──── none
T1  (OP07)  ──── none (LLM prior only)
T1  (OP06)  ──── esp-knowledge/deterministic/ YAML + optional pgvector
T2  (OP01)  ──── GET /api/telemetry (cced_esp :8000) → unlabelled.db opg_well_telemetry
                 GET /api/esp/assets/{id}/envelope
T3  (OP02–05) ── all T2 sources +
                 GET /api/vfd/diagnostics/{id} → in-memory VFD cache (normalized.db feed)
                 GET /api/esp/assets/{id}/health-index (legacy ML pipeline)
                 TDH physics (calculate_tdh MCP tool)
                 history_analytics → unlabelled.db (limit 60 rows, baseline deviations)
T4  (OP14)  ──── unlabelled.db opg_well_telemetry (history window, runtime/downtime segmentation)
T_FLEET     ──── GET /api/esp/assets (fleet list), per-asset simulate_frequency_change
```

---

## 9. LLM layer

- **Model:** Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf via llama-server (:8080)
- **Transport:** `LLMGateway` → `POST /v1/chat/completions`, `json_mode=True` (grammar-constrained JSON)
- **Repair:** `StructuredOutputValidator(AdvisoryOutputSchema).parse_with_repair()` — re-prompts on schema fail
- **Availability:** hard-checks `/health` + `/models`; falls back to deterministic advisory from live context (not canned text) if offline
- **Routing classification:** separate lightweight call — `max_tokens=20, temp=0.0`, picks one objective_id when semantic path < 0.78 confidence

---

## 10. Full flow in 10 steps (quick ref)

```
1.  Streamlit → execute_agent_query()
2.  UserEntryAdapter: resolve implicit well from Redis session memory
3.  IntentRouter: 4-path classify → objective + tier + ambiguity
4.  supervisor_graph.invoke() with thread_id for checkpointing
5.  Node 1–2: route objective, resolve asset context
6.  Node 3–4: tier-gated data load (telemetry / VFD / models / history / KB)
7.  Nodes 5–7: plan specialists → delegate loop → collect findings + evidence refs
8.  Node 8: assemble + freeze EvidencePack (authority-ranked, SHA-256 checksum)
9.  Nodes 9–10: conflict check + safety gate
10. Node 11: LLM synthesis (or deterministic for OP01/06/14) → StandardAdvisoryPayload
    → Streamlit renders progressive disclosure: assessment → evidence → hypotheses → recommendation → follow-ups
```

---

*Source files: `esp_agent/src/agent/supervisor/graph.py` (~1,530 lines), `user_entry.py`, `intent_router.py`, `agent_streamlit.py`*
