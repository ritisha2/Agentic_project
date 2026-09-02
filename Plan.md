# Plan — Conversational Wrapping of the ESP APM Backend

**Goal:** Turn the ESP APM agent (Agent Jane) from a single-shot "one query → one advisory" tool
into a real multi-turn conversational operator assistant, where **every kind of intent is routed
exactly to the correct objective** over live MQTT-fed data.

**Status legend:** ☐ not started · ◐ in progress · ☑ done

---

## Guiding principles (grounded in the live code + 2026 architecture research)

1. **Reuse, don't duplicate.** `CheckpointManager` (`esp_agent/src/agent/supervisor/checkpoint.py`)
   already does `esp:checkpoint:{run_id}` with Redis TTL + in-memory fallback via
   `RedisConnectionManager`. The conversation store **extends this same pattern** — no parallel
   Redis client, no new SQLite table.
2. **Memory is layered, not monolithic.** Research (O'Reilly *AI Agents Stack 2026*; the four-tier
   memory model — working / episodic / semantic / procedural) converges on: a fast ephemeral
   **session buffer** (Redis, TTL) for the live conversation, and an optional **long-term store**
   for cross-session recall. We build the session tier now (Level A) and leave a clean seam for the
   long-term tier (Level C) rather than pretending it exists.
3. **The router must see the conversation.** `IntentRouter.route(user_query, event_code)` today has
   **zero conversation context** — this is the single biggest structural gap. Injecting history into
   the LLM narrative alone does *not* fix routing; the router itself must receive prior turn context.
4. **Ambiguity is a first-class outcome.** `route()` must be able to say "I'm not sure" instead of
   silently defaulting to `OP03_FAULT_DIAGNOSIS`. That signal is what lets the graph ask a question
   back (HITL) instead of running a 30–70s graph on a guess.
5. **HITL needs a checkpointer on the graph.** Per LangGraph docs, `interrupt()` / pause-resume only
   works when the graph is compiled **with a checkpointer** and invoked with a stable `thread_id`.
   The graph today compiles with **no checkpointer** — that must change before Level B clarification.

---

## Architecture map — what "complete backend wrapping" actually touches

```
                    ┌─────────────────────────────────────────────────────────────┐
  Browser tab       │  Frontend (cced_esp/frontend-react)                           │
  X-Session-ID ────►│  AgentFloatingDock.jsx  — localStorage UUID, header on every  │
  (localStorage)    │  request; renders clarification questions as agent turns      │
                    └───────────────────────────┬─────────────────────────────────┘
                                                 │  POST /api/ui/agent/run  (+ X-Session-ID)
                                                 ▼
                    ┌─────────────────────────────────────────────────────────────┐
  BFF layer         │  bff_routes.py  — read X-Session-ID, resolve last_well,        │
                    │  inject recent turns, detect ambiguity, append each exchange  │
                    └───────────────────────────┬─────────────────────────────────┘
                                                 ▼
                    ┌─────────────────────────────────────────────────────────────┐
  Entry adapter     │  UserEntryAdapter.run(user_query, asset_id, session_id, ...)   │
                    │  — passes conversation_context into routing + graph           │
                    └───────────────────────────┬─────────────────────────────────┘
                                                 ▼
      ┌──────────────────────────┬──────────────────────────────┬───────────────────┐
      ▼                          ▼                              ▼                   ▼
┌───────────────┐   ┌───────────────────────┐   ┌───────────────────┐   ┌──────────────────┐
│ IntentRouter  │   │ ConversationStore     │   │ Supervisor graph  │   │ CheckpointManager│
│ .route(...,   │◄──┤ (NEW)                 │   │ (LangGraph)       │   │ (existing Redis) │
│  conv_ctx)    │   │ esp:conv:{session_id} │   │ + checkpointer    │   │ esp:checkpoint:* │
│ + ambiguity   │   │ Redis TTL 7d          │   │ + clarification   │   └──────────────────┘
│ + LLM fallback│   │ get_history/append/   │   │   node (interrupt)│
└───────────────┘   │ get_last_well         │   └───────────────────┘
                    └───────────────────────┘
                              │ (shares RedisConnectionManager)
                              ▼
                    ┌───────────────────────┐
                    │ Long-term memory tier │  ← Level C seam (episodic/semantic), not built yet
                    │ (vector / summary)    │
                    └───────────────────────┘
```

**Live data path (already wired, unchanged by this plan):**
`cced_esp` MQTT → `VFD WellDiagnosticEngine` → `/api/vfd/diagnostics/{well}` →
`LiveDataBridge.get_vfd_diagnostic()` → `EvidenceCollector.collect_from_vfd_diagnostic()` →
`ctx["vfd_diagnostic"]` → `CompactContextBuilder` → LLM.

---

# LEVEL A — Memory + Implicit Well (multi-turn for well-formed queries)

**Outcome:** A follow-up like "what about it?" resolves to the last well discussed, history is
injected into every LLM call, and the router can see prior turns. This is the agreed spec **plus**
the router-context change the spec omitted.

## Phase A1 — Conversation store (Redis, extends existing pattern)

- ☐ **A1.T1** Create `esp_agent/src/memory/conversation_store.py`.
  - `ConversationStore` reusing `RedisConnectionManager` from `checkpoint.py` (do **not** open a new
    client). Key scheme `esp:conv:{session_id}`, value = JSON list of turns, TTL 7 days.
  - Per-turn schema: `{role, content, timestamp, well_id, intent_detected}`.
  - Methods:
    - `append(session_id, role, content, well_id=None, intent=None)` — push turn, trim to last 20
      stored (serve last 10), refresh TTL.
    - `get_history(session_id, limit=10)` → most recent N turns (sliding window).
    - `get_last_well(session_id)` → most recent non-null `well_id` (implicit-well resolver).
    - `clear(session_id)`.
  - In-memory dict fallback when Redis is down (mirror `CheckpointManager`'s degradation behavior).
- ☐ **A1.T2** Unit-sanity (non-LLM): append 3 turns, assert `get_history` window + `get_last_well`.

## Phase A2 — Router sees conversation context

- ☐ **A2.T1** Extend `IntentRouter.route()` signature to
  `route(user_query, event_code=None, conversation_context=None)`.
  `conversation_context = {last_well, last_objective, recent_turns}`.
- ☐ **A2.T2** Follow-up resolution: when the query is a bare follow-up ("why?", "is that bad?",
  "what about it?") and `conversation_context.last_objective` exists, **carry forward the prior
  objective** instead of dropping to Path B → `OP03`.
- ☐ **A2.T3** Keep behavior fully backward-compatible when `conversation_context=None` (existing
  single-shot callers unchanged).

## Phase A3 — Entry adapter + BFF wiring

- ☐ **A3.T1** `UserEntryAdapter.run()` — accept `session_id`; when `asset_id` is missing, resolve via
  `ConversationStore.get_last_well(session_id)`; pass `conversation_context` into `route()` and thread
  `recent_turns` into the graph state for the LLM narrative.
- ☐ **A3.T2** `bff_routes.py` — read `X-Session-ID` header on `/api/ui/agent/run` and
  `/api/ui/agent/stream`; inject last 10 turns; append the completed exchange (both user + agent
  turns, with resolved `well_id` and `intent_detected`).
- ☐ **A3.T3** History injection into the prompt: extend `CompactContextBuilder` (or the prompt
  builder) with a compact `conversation_history` block (role + trimmed content only — no re-dumping
  evidence), bounded to stay within the small-model token budget.

## Phase A4 — Frontend session identity

- ☐ **A4.T1** `AgentFloatingDock.jsx` — generate a UUID once per tab, persist in `localStorage`, send
  as `X-Session-ID` on every agent request.
- ☐ **A4.T2** Confirm both `run` and `stream` paths send the header.

**Level A exit criteria:** "Status of FSWS-001-A?" → then "is that bad?" resolves to the same well
and a coherent follow-up objective, with history visible in the prompt. Verified by a real 2-turn
LLM run (user-run command, ~70s each).

---

# LEVEL B — Real conversation with a non-technical operator

**Outcome:** Vague/free-form language is either routed correctly by an LLM fallback, or the agent
**asks a clarifying question** instead of guessing. Requires new graph wiring.

## Phase B1 — Checkpointer on the graph (prerequisite for HITL)

- ☐ **B1.T1** Compile the supervisor graph **with a checkpointer** and invoke with a stable
  `thread_id` (= `session_id`). Per LangGraph, `interrupt()`/resume and cross-turn memory are
  impossible without this. Reuse the existing Redis connection; do not add a second persistence
  system.
- ☐ **B1.T2** Verify a run can pause and resume against the same `thread_id`.

## Phase B2 — Ambiguity scoring in the router

- ☐ **B2.T1** `route()` returns a real **ambiguity signal** (e.g. `RouteResult{objective, confidence,
  is_ambiguous, candidates}`) instead of always returning one objective. Stop the silent default to
  `OP03_FAULT_DIAGNOSIS`.
- ☐ **B2.T2** Define the trigger: `is_ambiguous = True` when confidence < threshold **and** no
  implicit well is resolvable from memory.

## Phase B3 — Clarification node (LangGraph interrupt / HITL)

- ☐ **B3.T1** Add a `clarification_node` early in the graph. When the router flags ambiguity and no
  implicit well exists, `interrupt()` with a clarifying question ("Which well — FS-031, FS-010…?")
  **before** the expensive evidence/LLM path runs.
- ☐ **B3.T2** Resume contract: the operator's answer resumes the same `thread_id`; the answer updates
  the well/objective and continues without replaying the whole graph.
- ☐ **B3.T3** BFF + frontend: render the clarifying question as a normal agent turn; the next user
  message resumes the paused run.

## Phase B4 — LLM-assisted routing fallback (full 14-objective coverage)

- ☐ **B4.T1** Add a lightweight LLM classifier fallback in the router: when keyword + semantic paths
  are both low-confidence, ask the office-server LLM to map free-form operator language → exactly one
  of the 14 objectives (constrained/enumerated output). Small prompt, cheap call.
- ☐ **B4.T2** Generalize greeting/small-talk: replace hardcoded exact-string matching ("hi",
  "hello") with an intent bucket that the LLM fallback can also land in ("morning, take a look at
  things?").
- ☐ **B4.T3** Cache/short-circuit: skip the LLM fallback when keyword/semantic already high-confidence
  (keep latency down).

**Level B exit criteria:** "morning, can you take a look at things?" with no well in context → agent
asks which well rather than fault-diagnosing a random asset; a clear technical phrasing still routes
in one shot with no extra LLM hop.

---

# LEVEL C — Durability & long-term memory (seam, build when needed)

**Outcome:** Cross-session recall and restart-safety. Not required for the conversational MVP; mapped
so the Level A/B design leaves clean seams instead of dead ends.

## Phase C1 — Long-term memory tier

- ☐ **C1.T1** Episodic/semantic store keyed per well (not per session) — summarized history that
  survives session expiry. Candidate: reuse existing vector infra (Qdrant `esp_kb`) with a separate
  namespace, or a rolling per-well summary written on session close.
- ☐ **C1.T2** Retrieval-into-prompt: surface "last time this well was discussed, the fault was X"
  when a new session opens on a known well.

## Phase C2 — Restart-safe long-running runs

- ☐ **C2.T1** Confirm checkpointer TTLs and thread_id survive a backend restart; a paused
  clarification can resume after a process bounce.

---

# Cross-cutting: known gaps to close alongside (mapped, not silently skipped)

- ☐ **X1 — Telemetry FALLBACK.** `TelemetryService` isn't reaching live `cced_esp` for the asset;
  all telemetry fields fall back to hardcoded constants (135/350/2100/1450/62/50/1.2). VFD diagnosis
  is correct, but the telemetry block the LLM sees is synthetic. Track and fix separately; note it in
  advisories until fixed.
- ☐ **X2 — Native VFD columns in DB.** Non-destructive `ALTER TABLE ADD COLUMN` for the 14 native VFD
  params (agreed earlier; not yet executed). Do **not** delete `labelled.db`/`unlabelled.db`.
- ☐ **X3 — Provenance/trace consistency.** Keep using `llm_adapter.last_trace` (not a re-probe) after
  the earlier race fix; confirm no hardcoded model name regressions.

---

# Sequencing recommendation

1. **Finish Task 4 verification first** (TASK4-E2E-003 real LLM run) — Level A touches the same
   `bff_routes` / `UserEntryAdapter` files, so confirm the VFD-context fix landed before layering
   memory on top.
2. **Level A end-to-end** (A1 → A4) — smallest change that delivers real multi-turn value.
3. **Level B** only after A is verified live — B1 (checkpointer) is the gate for B3 (clarification).
4. **Level C** when cross-session recall is actually requested.

---

## File change inventory

| File | Level | Change |
|------|-------|--------|
| `esp_agent/src/memory/conversation_store.py` | A | **NEW** — Redis session store |
| `esp_agent/src/agent/intent_router.py` | A, B | `conversation_context` param; ambiguity signal; LLM fallback |
| `esp_agent/src/agent/supervisor/user_entry.py` | A | `session_id`, implicit-well resolve, pass context |
| `esp_agent/src/api/rest/bff_routes.py` | A, B | `X-Session-ID`, inject history, append, render clarifications |
| `esp_agent/src/llm/context_builder.py` | A | compact `conversation_history` block |
| `esp_agent/src/agent/supervisor/graph.py` | B | compile with checkpointer; `clarification_node` (interrupt) |
| `cced_esp/frontend-react/src/components/AgentFloatingDock.jsx` | A, B | session UUID + header; render clarifications |
| `esp_agent/src/agent/supervisor/checkpoint.py` | A | (reuse only) `RedisConnectionManager` shared |

## Research sources
- O'Reilly — *The AI Agents Stack (2026 Edition)* (six-layer production agent model)
- MindStudio / markaicode — layered memory: ephemeral Redis session buffer + long-term vector store
- Four-tier agent memory model (working / episodic / semantic / procedural)
- LangChain LangGraph docs — checkpointers + `thread_id` for cross-turn memory; `interrupt()` HITL
- HITL engineering patterns — `thread_id` + checkpoint identity as the resumption contract

*Content from external sources was rephrased/summarized for licensing compliance.*
