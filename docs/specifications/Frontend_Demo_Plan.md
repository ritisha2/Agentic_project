# Final Plan — Agent Chat as a Fully Working Demo Assistant

**Goal:** Turn the existing React Agent Chat (`AgentFloatingDock`) into a generic, data-driven
conversational assistant. Any valid backend response renders in the existing UI with **no new
hardcoded route or answer per query**. Arbitrary natural-language ESP queries → intent-routed →
backend → normalized → rendered → follow-up with session context.

**Status legend:** ☐ not started · ◐ in progress · ☑ done

---

## Grounding facts (verified in code — this plan is built on these, not assumptions)

What already works (do NOT rebuild):
- **Streaming pipeline exists.** `agentApi.streamAgentRun()` reads NDJSON from `/api/agent/stream`;
  event types today: `status`, `text_delta`, `advisory`, `generative_ui`, `done`. `runAgent()`
  (sync) also exists. `X-Session-ID` is already sent on both (Level A4).
- **Backend already routes by intent, multi-turn, with fallback.** IntentRouter (Level A/B) handles
  arbitrary NL → 14 objectives, ambiguity → clarification (`interrupt()`/`ClarificationNeeded`),
  LLM-assisted routing fallback (B4), and a conversational fast-path for greetings/`OP07` in
  `bff_routes.py`. **The frontend does NOT need to do intent routing** — it must stop constraining
  the query and render whatever comes back.
- **Response deck exists.** `AgentResponseDeck` = 3 tabs: Advisory (markdown + action card),
  Evidence (`EvidenceCardsView`), Visualizations (`TelemetryVisualizerTab`).

What is actually hardcoded / missing (this plan's real targets):
1. **Forced asset pinning.** `handleSendMessage` sends `asset_id: selectedAsset || 'FS-010'` on
   *every* message → a NL query about another well is silently overridden. #1 blocker for "arbitrary
   queries." (Backend already resolves implicit well from session when asset_id is omitted — Level A3.)
2. **Hardcoded backend URL.** Vite proxy pins `http://127.0.0.1:8090`; no env-var config.
3. **Hardcoded error text.** The catch block hardwires "start `run_agent_server.py` on port :8090".
4. **Partial rendering of the response.** `StandardAdvisoryPayload` carries `assessment, diagnosis,
   confidence, risk, recommendation, expected_impact, constraints[], verification[], evidence[],
   provenance[], recommended_action{}`. Today only assessment/diagnosis (as narrative text) +
   recommendation (action card) + evidence + chart render. **`risk`, `expected_impact`,
   `constraints`, `verification`, `confidence` are dropped.**
5. **No response-shape abstraction.** `handleSendMessage` maps events ad-hoc inline. There is no
   normalization layer or render registry, so new payload kinds (metrics, tables) can't render
   without touching the handler.
6. **Clarification renders as plain text** — indistinguishable from a normal answer.
7. **No table/metrics block renderer** (backend does not emit tables today; renderer must be
   capable so it's future-proof, but the plan won't fake tables the backend can't produce).
8. **Chart is intent-blind + demo-fallback** — see Level F4 (has a hard backend dependency).

---

## Target architecture — one generic pipeline (no per-query branches)

```
 user types NL query
      │
      ▼
 AgentFloatingDock.handleSendMessage
      │  (send: {user_query, asset_id?}  + X-Session-ID)   ← asset_id OPTIONAL now
      ▼
 agentApi.streamAgentRun  ──NDJSON──►  /api/agent/stream (unchanged backend)
      │
      ▼
 normalizeAgentEvent(evt)        ← NEW: single funnel, event → canonical UiBlock[]
      │
      ▼
 message.blocks: UiBlock[]       ← canonical, render-kind-tagged
      │
      ▼
 <AgentResponseDeck> → BlockRenderer registry   ← NEW: kind → component, generic
      ├─ text        → AgentMarkdownRenderer
      ├─ metrics     → MetricsStrip (NEW)
      ├─ table       → DataTable (NEW, renders IF backend sends one)
      ├─ evidence    → EvidenceCardsView
      ├─ recommendation → ActionCard
      ├─ advisory_fields → Risk/Impact/Constraints/Verification blocks (NEW)
      ├─ visualization → TelemetryVisualizerTab
      ├─ clarification → ClarificationPrompt (NEW, distinct)
      └─ error/empty → StateBlocks (NEW)
```

The contract: **the frontend never inspects the query text to decide what to show.** It renders
whatever normalized blocks the response yields. Adding a query type on the backend needs zero FE
changes.

---

# LEVEL F1 — Generic request → response → render pipeline

**Outcome:** Any backend response renders through one normalization + registry path; all advisory
fields are shown; asset pinning and hardcoded config removed.

## Phase F1.1 — De-hardcode the request

- ☐ **F1.1.T1** Stop force-sending `asset_id`. Send `asset_id` only when the user explicitly picked
  an asset for *this* turn (e.g. first message, or dropdown just changed); otherwise omit it and let
  the backend resolve implicit well from session (Level A3). Never default to `'FS-010'`.
- ☐ **F1.1.T2** Env-var API config: introduce `VITE_AGENT_API_BASE` (and document `.env`), consumed
  by `agentApi.js` and the Vite proxy, replacing the hardcoded `http://127.0.0.1:8090`.

## Phase F1.2 — Normalization layer (NEW)

- ☐ **F1.2.T1** Add `src/services/agentResponseNormalizer.js`: `normalizeAgentEvent(evt, acc)` maps
  each NDJSON event to canonical `UiBlock`s appended to the active agent message:
  - `status` → transient status line (not a block)
  - `text_delta` → append to a `text` block
  - `advisory` → expand into blocks: `metrics` (confidence, risk horizon), `recommendation`
    (from `recommended_action`), `advisory_fields` (risk, expected_impact, constraints[],
    verification[]), `evidence` (evidence[])
  - `generative_ui` → `visualization` block
  - clarification signal (objective `CLARIFICATION` / status `CLARIFYING`) → `clarification` block
  - `done` → finalize
- ☐ **F1.2.T2** Normalizer is pure + unit-testable (no React), keyed only on event/field presence —
  never on query text.

## Phase F1.3 — Render registry (NEW) + full-field rendering

- ☐ **F1.3.T1** `BlockRenderer` maps `block.kind` → component. `AgentResponseDeck` iterates
  `message.blocks` through it. Unknown kind → safe generic JSON/text fallback (never crash).
- ☐ **F1.3.T2** New render components for currently-dropped data: `MetricsStrip` (confidence %,
  risk horizon, health if present), and an "Advisory detail" section rendering `risk`,
  `expected_impact`, `constraints[]`, `verification[]`.
- ☐ **F1.3.T3** `DataTable` component that renders a `table` block `{columns, rows}` **if** the
  backend emits one. (Backend emits none today — component ships dormant, ready; no fake tables.)
- ☐ **F1.3.T4** Preserve existing UI/UX: same tabs, same styling tokens, same animations — blocks
  slot into the existing Advisory/Evidence/Visualization tabs, not a redesign.

---

# LEVEL F2 — Robust conversational states

**Outcome:** Loading, streaming, error, empty, and clarification are all first-class — no hardcoded
failure text, no silent dead-ends.

## Phase F2.1 — Lifecycle states

- ☐ **F2.1.T1** Loading/streaming: keep the live status line; add a lightweight skeleton for the
  pre-first-token wait. Driven by `status` events, not timers.
- ☐ **F2.1.T2** Generic error state (`ErrorBlock`): replace the hardwired "run_agent_server.py"
  string with a real error surface (message + retry action). Distinguish transport error vs backend
  error payload.
- ☐ **F2.1.T3** Empty state: when a response yields no renderable block (rare), show a graceful
  "no structured result — here's the text" instead of a blank bubble.

## Phase F2.2 — Clarification & conversational (non-advisory) turns

- ☐ **F2.2.T1** `ClarificationPrompt` block: visually distinct (icon + "needs input" affordance),
  so a Level-B clarifying question doesn't look like a final answer. The user's next message resumes
  the paused run (backend `_pending_clarifications` already handles this).
- ☐ **F2.2.T2** Greetings / general ESP questions (`OP07` fast-path) return text-only with no
  advisory/chart — confirm the deck renders a clean text-only turn (no empty Evidence/Chart tabs
  shown). Tabs appear only when their block exists.

## Phase F2.3 — Intelligent fallback for unsupported/complex queries

- ☐ **F2.3.T1** For low-confidence/ambiguous intent, render the backend's clarification or LLM-
  fallback response as-is (already produced by Level B) — never a hardcoded "I can't do that."
- ☐ **F2.3.T2** If the backend returns an error/timeout, the `ErrorBlock` offers rephrase/retry —
  a useful dead-end, not a crash.

---

# LEVEL F3 — Multi-turn session UX (frontend surface of Level A/B)

**Outcome:** The chat *feels* like a continuous session; follow-ups visibly use context.

- ☐ **F3.T1** Confirm `X-Session-ID` persists across turns in a tab (Level A4 — already sends it)
  and that follow-ups ("is that bad?", "why?") work end-to-end through the UI without re-specifying
  the well. This is the FE validation of Level A implicit-well + follow-up routing.
- ☐ **F3.T2** Optional lightweight "context" affordance: show the currently-implied well (e.g. a
  subtle chip "Context: FSWS-001-A") so the operator sees what a bare follow-up will act on. Read-only
  reflection of backend session state; no new client-side routing.

---

# LEVEL F4 — Intent-driven visualization (HAS A BACKEND DEPENDENCY — flagged)

**Outcome:** The chart reflects what the user asked for and the actual finding, not a fixed
production/pressure chart. **Cannot be done frontend-only** — the FE already renders arbitrary
traces; the *selection* of what to plot lives in the backend.

- ☐ **F4.T1 (backend, dependency)** Backend emits an intent-appropriate trace set: map
  `objective_id` + primary fault → signals (e.g. backpressure → discharge/WHP/FLP; vibration →
  vibration trend; production decline → flow vs BEP). Enabled by the X2 native VFD columns now in the
  historian. **This modifies backend chart logic — out of the pure FE↔BE contract; needs explicit OK.**
- ☐ **F4.T2 (backend, dependency)** Replace the `default_data` demo arrays (`[1750,1720,…]`) with an
  honest "no timeseries available" signal when live data is absent (mirrors the X1 telemetry-flag fix)
  so the UI never renders fiction.
- ☐ **F4.T3 (frontend)** Render the "no timeseries" state in the Visualization tab instead of a fake
  chart; render whatever real intent-selected traces arrive (renderer is already generic).

> If you want to keep this pass strictly frontend/no-backend-change, F4 is deferred and the chart
> tab simply shows an honest empty state when data is synthetic — still an improvement over the
> current misleading demo chart.

---

# Demo acceptance matrix (how we prove "no per-query hardcoding")

| Query kind | Example | Expected render | Proves |
|---|---|---|---|
| Greeting | "hi" / "morning" | text-only turn, no empty tabs | OP07 fast-path + text block |
| General ESP | "what can you check on an ESP?" | text | generic text, no route added |
| Asset status | "status of FSWS-001-A" | metrics + advisory fields + evidence (+chart) | full-field render |
| Analytical | "why is backpressure high on FSWS-001-A?" | diagnosis + evidence + viz | normalization, not query-matching |
| Follow-up | "is that bad?" (no well) | resolves same well, coherent answer | Level A session via UI (F3) |
| Ambiguous | "is everything okay?" | distinct clarification prompt | F2.2 + Level B |
| Backend error/timeout | (server down) | ErrorBlock + retry | F2.1, no hardcoded string |

**Pass condition:** every row works with the SAME code path — no `if query.includes(...)` branch,
no per-query response object.

---

## File change inventory (frontend unless noted)

| File | Level | Change |
|---|---|---|
| `frontend-react/src/components/AgentFloatingDock.jsx` | F1.1, F1.3, F2 | drop forced asset_id; render `message.blocks` via registry; wire states |
| `frontend-react/src/services/agentApi.js` | F1.1 | env-var base URL |
| `frontend-react/vite.config.js` | F1.1 | proxy target from env |
| `frontend-react/.env` (+ `.env.example`) | F1.1 | `VITE_AGENT_API_BASE` |
| `frontend-react/src/services/agentResponseNormalizer.js` | F1.2 | **NEW** event → UiBlock[] |
| `frontend-react/src/components/blocks/BlockRenderer.jsx` | F1.3 | **NEW** kind → component registry |
| `frontend-react/src/components/blocks/MetricsStrip.jsx` | F1.3 | **NEW** |
| `frontend-react/src/components/blocks/AdvisoryDetail.jsx` | F1.3 | **NEW** risk/impact/constraints/verification |
| `frontend-react/src/components/blocks/DataTable.jsx` | F1.3 | **NEW** dormant until backend emits tables |
| `frontend-react/src/components/blocks/ClarificationPrompt.jsx` | F2.2 | **NEW** |
| `frontend-react/src/components/blocks/StateBlocks.jsx` | F2.1 | **NEW** loading/error/empty |
| `frontend-react/src/components/AgentResponseDeck.jsx` | F1.3, F2 | iterate blocks; tabs conditional on block presence |
| `esp_agent/src/api/rest/bff_routes.py` | **F4 (backend)** | intent→trace selection; honest no-data (needs OK) |

---

## Sequencing

1. **F1** (normalizer + registry + de-hardcode) — the backbone; everything else slots onto it.
2. **F2** (states + clarification) — makes it demo-safe and complete.
3. **F3** (session UX validation) — largely verification of existing Level A/B through the UI.
4. **F4** (intent-driven viz) — **only if** you approve backend chart changes; otherwise ship the
   honest empty state and defer.

## Scope guardrails
- Preserve UI/UX: reuse existing tabs, tokens, animations — no visual redesign.
- No new hardcoded per-query branches anywhere — enforced by the normalizer + registry design.
- Backend logic unchanged **except F4** (visualization), which is explicitly flagged as requiring
  backend edits and your sign-off.
- Dashboard widgets (`FleetHealthGrid`, `LiveTelemetryTable`, etc.) are **out of scope** for this
  chat-focused plan and **not yet audited** for mock data — flag separately if you want them covered.
