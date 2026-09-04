# ESP Agentic Platform — Implementation Plan

**Status of this document:** written after a full codebase + data audit on 2026-09-04. Supersedes any prior plan drafts in chat history. Every phase below is grounded in confirmed current-state findings (file paths, line numbers, row counts) — not assumptions.

---

## 0. Audit findings this plan is built on

### 0.1 Data layer (confirmed via direct SQL + `git log`)

| Store | Size | Rows | Notes |
|---|---|---|---|
| `cced_esp/data/unlabelled.db` → `opg_well_telemetry` | 14.68 GB | 3,110,985 | Live MQTT historian. 34 columns incl. 9 native VFD params. 29 `well_id` / 44 `asset_id`. Span confirmed: **2026-08-31 06:10 → 2026-09-03 13:11 (~3 days)**, not 6 months. |
| `cced_esp/data/labelled.db` → `opg_well_telemetry` | 12.98 GB | 3,110,985 | Mirror schema, parallel write. |
| `cced_esp/data/normalized.db` → `opg_normalized_telemetry` | 1.19 GB | 3,110,985 | **New** precomputed feature store. Live triple-write from `mqtt_collector.py`. Now the primary read source for `dashboard.py` and the VFD cache pre-warm. |
| `esp_events.db` (root + `esp_agent/`) | ~20 KB | — | Event store, unrelated to telemetry volume. |

**OPEN QUESTION — must be answered before Phase 1:** the "six months of historical data" referenced in the meeting has not been located. It is not in `cced_esp/data/`, not in `code/models/categorized_wells` (path does not exist), and `data/advait` / `data/references` were not fully inventoried (session interrupted mid-audit). **Action: locate this dataset explicitly before Phase 1 starts** — do not assume the 3-day `unlabelled.db` window is it.

### 0.2 ML model layer (`code/models/`) — canonical, current

- `fault_classifier.py` (313 lines, committed `1741188`): **13 rule-based faults + Normal Operation + a 14th "Well Offline / Standby" gate.** The Standby gate is a hard `return` immediately after raw-value extraction, before any dynamics/scoring: if `VFD STS <= 0.1` and `amps < 1.0` → returns `primary_fault="Well Offline / Standby"`, health 0, confidence 100%, status `⚪ STANDBY`. This eliminates false-fault-flooding on idle/parked wells.
- `anomaly_detector.py` + `diagnostic_engine.py`: **uncommitted local changes** (confirmed present via `git status`) replacing a synthetic-noise self-fit with per-well → per-family → global Isolation Forest baseline calibration (`fit_from_registry()`), fitted from real `well_calibration_registry.json` statistics. Confirmed independent of the Standby gate (anomaly scoring always runs; Standby only short-circuits the fault classifier).
- **Not yet committed** — needs a commit once Phase 1 verification passes.
- Legacy parallel system: `cced_esp/ml/` (5-model scaffold: rule_engine/fault_classifier/risk_predictor/rul_engine/anomaly_detector) was deleted as "deprecated," broke `unified_pipeline.py`/`decision_service.py`/`esp_routes.py` imports, and was restored as **source only** — trained `.joblib` artifacts were never restored. This pipeline now runs without crashing but its classifier/risk/RUL/anomaly stages operate on unloaded models. **This is a live latent bug**, independent of anything in this plan, and should be flagged to whoever owns `cced_esp/ml/`.

### 0.3 Visualization layer — already exists, do not rebuild

- `code/eda/figure_factory.py` (233 lines): genuinely pure (`data-in → go.Figure/DataFrame out`, no `st.*`/SQLite/HTTP). Two functions: `render_incident_tipping_timeline()` (3-row synchronized subplot with per-well dynamic normal-corridor bands + incident marker) and `build_evidence_comparison_table()` (trip-instant vs. baseline deviation table). Backed by a real anti-hardcoding test suite (`code/tests/test_figure_factory_forensics.py`, 5 tests, including a live end-to-end Standby regression test).
- `code/eda/dashboard.py` (~1830 lines): real 8-tab Streamlit ML dashboard. Tab 7 ("Fleet Fault Finder") is the forensic deep-dive, wired to `figure_factory.py`, with a data-lineage badge and adaptive time-resolution defaulting. Reads `unlabelled.db` + `normalized.db`; **never reads `labelled.db`**.
- **Implication:** the "dynamic visualization engine" work is now *extend the existing pure-function pattern and connect it to agent chat*, not build from zero.

### 0.4 Streamlit agent app (`agent_streamlit.py`) — 781 lines, refactored twice since this session started

- Single full-width conversational chat UI (old multi-tab dashboard layout removed).
- Real additions: `BackendCircuitBreaker` (prevents UI-thread freezing on backend outage) and an O(1) `discover_active_assets()` registry cache (reads `well_calibration_registry.json` dict keys, never scans the multi-million-row telemetry table).
- **Fixed since last audit:** the blanket `92.5/NORMAL` fabrication is gone — genuine unavailable states now return `"_source": "unavailable"`, `"⚪ NO LIVE DATA"`.
- **Residual gap:** per-field silent defaults (e.g. `confidence = ... or 0.95`, boilerplate "Engineering Derivation" text) can still surface inside a response labeled as `_source: "backend_api"`/`"in_process"`, with no per-field honesty marker.
- **Critical architecture gap:** it runs the LangGraph agent **in-process** (`UserEntryAdapter().run()`/`.resume()` called directly in the Streamlit process) — it does **not** call the BFF's `POST /api/ui/agent/stream` HTTP contract at all. This is the real "Streamlit ↔ backend sync" gap: two different runtime paths exist for the same agent, and they can drift.

### 0.5 Knowledge base — split-brain (the most important finding)

Two unrelated knowledge systems exist, and **production chat uses the one that was not fully audited in earlier sessions**:

1. `esp_agent/knowledge_bases/esp/` — real content (objectives ×14, event mappings, mapping_config, telemetry fixture), but its `documents/` (4 files, thin), `graph/esp_graph.json` (real, ~12 entities, 6 causal edges), and `rules/diagnostic_rules.json` (9 threshold rules) are **only reachable through the legacy `DiagnosticAgentRuntime`/CLI path** (`src/api/cli.py`, `POST /diagnose`), not through production chat.
2. `esp-knowledge/deterministic/` (8 files across faults/alerts/glossary/model_semantics/objectives/policies/units) + Postgres/pgvector (`knowledge_embeddings` table) — **this is what the production `knowledge` specialist (`RetrievalService.hybrid_retrieve()`) actually queries.** Whether Postgres/pgvector is actually running in this environment is unconfirmed (`psycopg2`/`redis` are installed; live connectivity not verified).

**Net finding:** the production agent's actual knowledge grounding is thin (8 files) and disconnected from the richer causal graph and rules that exist elsewhere in the repo. This is the real blocker for "Knowledge base + Data + History fused" from the meeting — bigger than the funnel or the visualization gap.

### 0.6 Backend (`cced_esp`, submodule, actively evolving)

- VFD diagnostic cache now **pre-warms up to 50 wells proactively at startup** (background thread reading `normalized.db`), not purely MQTT-reactive. This is a positive change for the "evidence-tier funnel" design — status/history queries can now be served from a warm cache without waiting on live MQTT traffic.
- Historian routes (`/api/v1/historian/...`) read `unlabelled.db` with dynamic-window anchoring (anchors to `MAX(timestamp)` in DB, not wall-clock `now()`).
- `ml_telemetry_routes.py` (broker-authenticated bulk telemetry export, `/api/v1/telemetry/unlabelled[...]`) was **deleted with no replacement**. Flag before Phase 1 if any external ML/analytics consumer depends on it.
- `archive/ccep_deprecated.zip` genuinely contains dead legacy frontends (vanilla-JS + old React app) — safe to ignore. It also transiently contained the `ml/` package described in 0.2 before restoration.

---

## Guiding principles (unchanged from prior discussion, now grounded)

1. **On-prem only.** No cloud dependency. LLM is already local (Qwen via llama-server). Confirm Postgres/pgvector/Neo4j/Redis are all local instances, not managed cloud services, before Phase 4.
2. **Routing is the foundation.** Intent + conversation context decide objective, tier, and depth before anything else runs.
3. **Depth follows tier.** The full chain (*Observation → Trend → Expected model → Actual vs Expected → Contributing parameters → ML anomaly → Ranked hypotheses → Evidence → Confidence → Recommendation → Follow-up*) is the **full-diagnostic tier contract only**. Vague/simple queries get short, honest answers.
4. **One backend contract.** `agent_streamlit.py` must become a client of the same NDJSON stream the React UI uses — not a second in-process runtime.
5. **Fuse three real sources per answer**: Knowledge Base + Data (live/normalized) + History (unlabelled.db time range) — never generic LLM knowledge alone.
6. **No duplicate code.** Extend `figure_factory.py`'s pure-function pattern; do not reimplement plotting inline elsewhere.
7. **Clean as we go.** Commit the pending anomaly-detector fix; resolve the KB split-brain; don't leave two parallel knowledge systems live.

---

## Phase 0 — Close open questions & stabilize the base (no new features)

**0.A — Locate the six-month dataset.**
- Action: ask the user directly for the exact path/source of the six-month historical dataset (it is not in this workspace's known data directories).
- Verify: dataset located, its schema/columns compared against `opg_well_telemetry`'s 34 columns, coverage/gaps profiled.

**0.B — Commit the pending model fix.**
- Files: `code/models/anomaly_detector.py`, `code/models/diagnostic_engine.py`.
- Action: run the existing forensics test suite (`code/tests/test_figure_factory_forensics.py`) plus a manual per-well/family/global calibration spot-check (already done earlier this session — normal wells read as inliers with probability 0.15–0.26, not the old fabricated ~90%); commit with a clear message.
- Verify: `git status` clean on these two files; test suite passes.

**0.C — Resolve the KB split-brain.**
- Files: `esp_agent/knowledge_bases/esp/` vs `esp-knowledge/deterministic/`.
- Action: decide (with the user) which is canonical going forward. Likely: consolidate into one, migrate the richer causal graph (`esp_graph.json`) and `diagnostic_rules.json` into whichever path production chat actually uses.
- Verify: `RetrievalService.hybrid_retrieve()` and the `knowledge` specialist draw from a single, documented KB location; no orphaned duplicate KB remains reachable only by dead code paths.

**0.D — Flag the `cced_esp/ml/` unloaded-model bug and the deleted `ml_telemetry_routes` externally.**
- Action: confirm with the user/ML team whether these are known/acceptable or need fixing; out of scope for this plan unless they say otherwise.

**0.E — Fix the Streamlit/BFF stream contract mismatch (prerequisite for Phase 6).**
- Files: `esp_agent/src/api/rest/bff_routes.py`, `esp_agent/src/api/fastapi_app.py`.
- Action: confirm `UIAdvisoryRunRequest.user_query` required-field behavior (422 root cause identified earlier); remove the double `/api/ui` mount in `fastapi_app.py`.
- Verify: valid `POST /api/ui/agent/stream` → 200 NDJSON; missing `user_query` → clear 422; no `/api/ui/api/ui/...` route resolves.

**0.F — Build the demo verification harness.**
- Action: encode the meeting's five acceptance questions + a routing regression set as one scripted harness against the live NDJSON stream.
- Verify: harness runs and records, per query: routed objective, tier, tool-calls made, evidence sources + KB mapping, viz spec emitted. This is the single regression gate for every later phase.

**Phase 0 done when:** dataset location is known, the model fix is committed and tested, one KB is canonical, the stream contract works, and the harness runs end-to-end (even if most assertions fail — the point is it *runs*).

---

## Phase 1 — History intelligence layer (turn raw data into usable history)

Goal: whatever historical dataset is confirmed in 0.A becomes queryable, quality-profiled, and analytics-ready — the substrate for every operational question ("why did it stop", "how many hours").

**1.1 — Profile & data-quality report.**
- Per-signal coverage, blank/missing periods, units, sampling gaps across the confirmed historical dataset.
- Verify: written coverage report (signal × time-window completeness), explicit list of fields present only for limited periods.

**1.2 — Normalize & load into the history layer.**
- Clean, unit-normalize, gap-tag; load into `opg_well_telemetry` (extending the existing schema) or a dedicated history table. Missing data flagged, never fabricated/zero-filled.
- Verify: row counts + time span match source; missing periods are marked, not interpolated silently; spot-check queries by well + time window return expected ranges.

**1.3 — Operational analytics primitives.**
- Derive, directly from history: run/stop **state segmentation** (using the same VFD-status + amps logic as the new Standby gate, for consistency), **runtime hours**, **downtime episodes** (start/end/duration), **production totals** (flow integrated over time), **stop events** with the pre-stop signal window.
- Verify: for a known well+period, computed runtime/downtime/production reconcile against a manual spot-check on raw data.

**Phase 1 done when:** the demo questions ("how many hours", "how much production", "how much downtime") have a computed, correct, evidence-cited answer path — before any LLM/agent work touches them.

---

## Phase 2 — Routing & intent understanding (foundation, highest leverage)

**2.0 — Fix the Path B silent-default misroute (confirmed bug, do this first).**
- File: `esp_agent/src/agent/intent_router.py`, Path B (semantic/token-overlap) block inside `route()`.
- Root cause (confirmed by reading the live code, not assumed): the semantic scorer seeds `best_obj_id = "OP03_FAULT_DIAGNOSIS"` before any match is attempted:
  ```python
  best_score = 0.0
  best_obj_id = "OP03_FAULT_DIAGNOSIS"   # ← seeded default, not "no match"
  ```
  If the query has zero real keyword/title overlap with any objective, `best_score` stays `0.0` and `semantic_confidence` lands at exactly `0.5` — correctly below both the LLM-fallback threshold (`0.60`) and the ambiguity threshold (`0.65`), so today's safe cases (a truly empty-overlap, unanchored query) do get caught and routed to the LLM or clarification.
  The actual failure mode is narrower: **one weak, accidental token overlap** (a single shared word against some objective's title `+0.2` or description `+0.1`) is enough to push `semantic_confidence` to `0.60` exactly. The LLM-skip check is `if semantic_confidence < _LLM_FALLBACK_THRESHOLD` (strict `<`), so `0.60` **skips the LLM entirely**. And if the query happens to name a well, or a well is already anchored in session (`conversation_context["last_well"]`), the ambiguity clarify is also suppressed regardless of match quality. Net effect: a genuinely-unmatched query can silently execute the full `OP03_FAULT_DIAGNOSIS` pipeline — the most expensive, most consequential objective — with no keyword actually matching it, no LLM confirmation, and no clarification.
- Fix (two small, targeted changes, not a router rewrite):
  1. Change the seed default from `"OP03_FAULT_DIAGNOSIS"` to `"OP07_GENERAL_INQUIRY"` (or `None`, forcing the LLM-fallback branch unconditionally when nothing scores above 0). "No real match" must never masquerade as "diagnose a fault."
  2. Tighten the LLM-skip / ambiguity-bypass condition so a single low-value description-only overlap (`+0.1`) can't cross the `0.60` boundary on its own — e.g. require at least one real **title**-token match (`kw_matches`, not just `desc_matches`) before the score is allowed to skip the LLM check.
- Verify (before/after, using the harness from 0.F):
  - **Before:** construct a query with exactly one accidental shared token against `OP03_FAULT_DIAGNOSIS`'s title/description and a named well, e.g. one deliberately picked to land `semantic_confidence == 0.60` — confirm it currently skips both the LLM fallback and the ambiguity clarify and silently returns `OP03_FAULT_DIAGNOSIS`, `Path_B_Semantic`.
  - **After:** the same query either routes to `OP07_GENERAL_INQUIRY` (if truly no real match) or triggers the LLM-fallback/clarification path — it must never silently land on a full-diagnostic objective without a real keyword, semantic, or LLM-confirmed signal.
  - Regression: re-run every existing routing case from the earlier audit (greetings, "why" follow-up, event mapping, deterministic keyword matches) and confirm none of them change behavior — this fix only touches the zero/weak-match seed path.

**2.1 — Context-aware intent resolution.** Extend `esp_agent/src/agent/intent_router.py` to genuinely use `conversation_context` (last_well, last_objective, recent_turns) in the semantic layer, not just the ~14 exact-match follow-up phrases.
**2.2 — Slot/parameter extraction.** Parse quantities/references from follow-ups (`52 Hz`, `last week`, pronouns) into a `params` dict carried with the objective.
**2.3 — New operational-history objective.** Add an objective (e.g. `OP14_OPERATIONAL_HISTORY`) routed to the Phase 1 analytics, distinct from the live fault-diagnosis objective — "why did it stop" is a history-reasoning question, not a live VFD diagnosis.
**2.4 — Confidence-gated clarification.** Below-threshold, unanchored queries ask one crisp question instead of running the full pipeline.
**2.5 — Routing regression suite.** ~30 labeled queries (greetings, procedure lookups, status, faults, decline, fleet, the 5 demo questions, follow-ups, ambiguous, **plus the 2.0 weak-overlap edge case**) with expected objective + tier + ambiguity flag; gate for every later phase.

**Phase 2 done when:** the harness (0.F) shows correct routing for all demo questions + the regression set (including the 2.0 fix), and follow-ups carry extracted parameters. No query lacking a real keyword/semantic/LLM-confirmed match may silently resolve to `OP03_FAULT_DIAGNOSIS` or any other full-diagnostic objective.

---

## Phase 3 — Evidence-tier funnel + tier-aware response anatomy

**3.1 — `evidence_tier` on objectives.** Tiers: `T1_KB_ONLY` (OP06/OP07), `T2_SNAPSHOT` (OP01), `T3_FULL_DIAGNOSTIC` (OP02/03/04/05), `T_HIST` (new OP14, pulls Phase 1 analytics + KB), fleet stays its own branch.
**3.2 — Gate context loading by tier.** In `esp_agent/src/agent/supervisor/graph.py` (`data_quality_gate_node`, `load_minimum_context_node`): T1 skips telemetry+model+VFD; T2 loads telemetry+engineering only; T3/T_HIST load everything relevant to their tier.
**3.3 — Tier-aware response contract.** Extend `StandardAdvisoryPayload` (`esp_agent/src/schemas/advisory.py`) with `trend`, `expected_vs_actual`, `contributing_parameters`, `ml_anomaly`, `ranked_hypotheses` (full list), `uncertainties`, `follow_up_question`. Populate by tier — full chain only at T3/T_HIST.
- Verify: audit trail proves tool-calls per tier; a T1 procedure lookup has zero model/telemetry calls; a T3/T_HIST query has every chain field populated from real evidence.

**Phase 3 done when:** response depth measurably scales with objective tier, provable from both the audit trail and the payload shape.

---

## Phase 4 — Operational history reasoning (the demo core)

Fuse Data + History + KB to answer the meeting's acceptance questions correctly, with WHY.

**4.1 — Answer computation** from Phase 1 primitives — hours/production/downtime are deterministic, exact, not LLM-estimated.
**4.2 — "Why did it stop" reasoning** — take the pre-stop signal window (from 1.3), match against fault signatures (the 14-state classifier + the causal graph resolved in 0.C), produce a grounded cause with contributing parameters.
**4.3 — Grounded explanation** — every answer returns the computed value + the exact history window/evidence used + the KB citation for any causal claim.
- Verify: each of the five demo questions returns a technically correct value, cites the exact history window, and (for "why") cites the correct KB/causal source — checked against manual analysis on the confirmed dataset.

---

## Phase 5 — Fused evidence surface + KB-mapping verification

**5.1 — Wire the dead collectors.** `esp_agent/src/services/evidence/collector.py::collect_from_historian()` and `collect_from_knowledge_graph()` are defined but never called by `context_builder.py::build_evidence_pack()` — wire them in.
**5.2 — KB-mapping verification test.** The meeting's explicit validation point: `Query → Answer → Evidence → correct KB/source mapping`, not just `Query → Answer`. Build a test that every cited evidence item resolves to the real, correct KB document/section (post-0.C consolidation).
- Verify: T3/T_HIST packs contain history + KB + causal items; mapping test passes for the demo questions with no dangling/mismatched citations.

---

## Phase 6 — Dynamic visualization & dashboard composition (extend, don't rebuild)

**6.1 — Extend `figure_factory.py`'s pure-function pattern**, not `schemas/visualization.py`'s currently-hardcoded single chart. Add builders for the other spec types (pump curve, scenario/what-if, prediction, timeline) following the exact same signature style already proven by `render_incident_tipping_timeline()`.
**6.2 — Deterministic selector** — objective/fault/params → which figure_factory function(s) to call. "Create a dashboard for FS-031" composes multiple real figures (trend + evidence table + incident timeline) into one view, all sourced from `normalized.db`/`unlabelled.db` like the existing Tab 7 pattern.
**6.3 — Constrained LLM fallback** only for ambiguous cases — type + params only, Pydantic-validated, never executes LLM code.
**6.4 — Wire into the BFF stream** (`esp_agent/src/api/rest/bff_routes.py`) replacing the currently-hardcoded `plotly_chart` block.
- Verify: "create a dashboard" composes a real multi-panel view from that well's actual history; a procedure lookup emits no chart; the anti-hardcoding test pattern from `test_figure_factory_forensics.py` is replicated for every new builder.

---

## Phase 7 — Streamlit agent app ↔ backend sync (close the architecture gap)

**7.1 — Switch from in-process to the BFF HTTP contract.** Replace `agent_streamlit.py`'s direct `UserEntryAdapter().run()`/`.resume()` calls with `POST /api/ui/agent/stream` + `X-Session-ID`, matching what the React UI uses. This eliminates the two-runtime-path drift risk identified in 0.4.
**7.2 — Render the real event stream** — `status`, `text_delta`, tier-aware `advisory`, composed `generative_ui` dashboards (Phase 6), evidence-with-KB-source links, follow-up chips that resume the session.
**7.3 — Close the remaining per-field honesty gap.** Remove silent per-field defaults (confidence `0.95`, boilerplate derivation text) identified in 0.4; either compute the real value or label it explicitly as unavailable, consistent with the already-fixed blanket-fabrication case.
- Verify: the five demo questions run end-to-end in Streamlit via the BFF contract, showing correct answers, composed dashboards, KB-mapped evidence, and working follow-ups; with the backend down, every field shows an honest unavailable state — no silent defaults.

---

## Execution order

**Phase 0 → Phase 1 ∥ Phase 2 (parallel) → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7.**

Phase 0 is mandatory and mostly non-code (locate dataset, commit pending fix, resolve KB split-brain, fix stream contract, build harness). Phases 1 and 2 can run in parallel since history-layer work and routing work touch different files. Every phase after 0 is gated by the harness built in 0.F — no phase is "done" until the harness shows it didn't regress the demo questions.

## What changed from the prior (pre-audit) plan

- Added **Phase 0 open questions** (dataset location, KB split-brain, pending uncommitted fix) that must close before feature work — none of these were visible without this audit.
- **Phase 1 (history layer)** is now upstream of routing, because the demo questions are fundamentally history-analytics questions, not live-diagnosis questions.
- **Visualization phase (6) is now "extend `figure_factory.py`"**, not "build from `schemas/visualization.py`" — the audit found a real, tested, pure-function pattern already in production that the prior plan didn't know about.
- **Streamlit sync (7) is now a concrete architecture fix** (in-process → BFF HTTP contract) rather than a generic "sync" task — the audit found the exact mechanism of drift.
- **KB consolidation (0.C) is new** — the prior plan assumed one KB; the audit found two, with production chat using the thinner, less-audited one.
