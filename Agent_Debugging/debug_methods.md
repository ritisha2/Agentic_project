# Architecture Methodologies for Layered Agentic Systems
Incorporation doc — handoff integrity, mock/hardcode elimination, multi-agent state

## 1. Explicit Handoff Contracts

**Problem addressed:** Layer N's output is not "listened to" by Layer N+1; receiving layer either re-derives its own version or falls back to defaults/mocks.

**Methodology:**
- Every inter-layer or inter-agent message is a typed, versioned schema (Pydantic/Zod), not free text.
- Schema declares: required fields, value ranges/units, allowed error codes, provenance field (source system/tool/query that produced this value), confidence field.
- Receiving layer validates against schema BEFORE consuming. Validation failure = hard stop, not silent fallback to mock/default.
- Contract changes are versioned and diffed like an API; all dependent agents must be updated in lockstep, enforced via CI.

**Incorporation steps:**
1. Define a `HandoffPacket` base schema: `{payload, provenance, confidence, schema_version, producer_id, timestamp}`.
2. Wrap every agent/tool output in this packet before it crosses a layer boundary.
3. Add a validation gate function that every consuming layer must call first; log validation failures as first-class events, never swallow them.
4. Add contract version checks to CI so a producer/consumer schema mismatch fails the build, not the runtime.

Source: multi-agent orchestration handoff-contract pattern; hallucination-cascade prevention via schema validation.[web:2][web:9]

## 2. Shared Context / State Layer (No Fragmented Re-Fetching)

**Problem addressed:** Each phase/agent reconstructs its own context from scratch, drifting from what previous phases already established — root cause of "it continues with its own mock data."

**Methodology — three mandatory layers:**
- **Hot shared memory:** Redis (or equivalent) as a typed blackboard readable/writable by authorized agents. Use optimistic locking or CRDTs — never allow two agents to mutate the same key without a conflict strategy (race conditions here are the leading cause of silent multi-agent bugs).
- **Append-only event log:** Kafka/Redpanda/partitioned Postgres. Every agent action, tool call, and handoff emits an immutable event. Gives full auditability, replayability, and point-in-time state reconstruction.
- **Checkpointing:** Persist a compact snapshot of control-flow position + minimal resume state at every handoff. Converts a crash into a resumable pause instead of a restart-from-mock.

**Incorporation steps:**
1. Stand up one shared state store (Redis or Postgres) as canonical source of truth for cross-phase variables — no agent/layer maintains a private copy of a value another layer already owns.
2. Add an event bus/log; every phase transition writes an event before proceeding.
3. Use a checkpointer library (LangGraph `Checkpointer`, AutoGen durable runtime) at every major phase boundary so resumption never requires regenerating prior-phase outputs from scratch.
4. Rule: promote data to shared state only when a downstream layer demonstrably needs it — don't over-centralize.

Source: multi-agent state management layering (shared memory, event log, checkpointing).[web:2][web:9][web:14]

## 3. Verification/Gating Layer at Every Handoff Boundary

**Problem addressed:** Hallucinated, mocked, or hardcoded content from one layer is accepted uncritically by the next, then propagates and compounds.

**Methodology (Handoff Verification Layer pattern):**
Insert a lightweight intermediary between every producer and consumer layer performing, in order:
1. Claim extraction from producer output.
2. Recursive grounding check against the original source-of-truth document/data (not just the immediately preceding layer's output).
3. Local consistency check against previous context.
4. Confidence calibration score attached to output.
5. Authenticity/plausibility scoring.
6. Compression/summarization before forwarding, preserving epistemic status flags (i.e., "this claim is unverified" travels forward instead of being silently dropped).

**Gating rules:**
- Confidence below threshold → block, do not forward; route to human review or a recovery agent.
- Two layers referencing the same upstream value with different magnitudes/units → flag as structural anomaly automatically.
- Terminal/final layer must re-verify key claims against the original input, not against intermediate layer outputs only.

**Incorporation steps:**
1. Build a `verify_handoff(payload, source_of_truth)` function library — even a rule-based version (regex/range checks) is a large improvement over nothing.
2. Attach confidence + provenance to every payload (ties into contract in Section 1).
3. Define per-domain thresholds (e.g., financial values need higher confidence than draft copy text).
4. Log every gate decision (pass/block/escalate) as an event (ties into Section 2's event log).

Source: Handoff Verification Layer / handoff-hallucination taxonomy; cross-agent consistency checks.[web:8][web:9]

## 4. Mock/Hardcode Lifecycle Management (Anti-Scaffolding-Leak Policy)

**Problem addressed:** Agentic IDEs hardcode/mock data to "look done," and that scaffolding survives into what's presented as production output — the exact failure mode you described.

**Methodology:**
- Separate configuration from logic: endpoints, credentials, dataset paths never embedded in generated business logic — always externalized (env vars/config), per 12-factor principles.
- Mandatory tagging: any temporary mock/hardcoded value the agent introduces must be emitted with a machine-readable marker (e.g., `# MOCK_SCAFFOLD: reason, expiry-condition`), not just a comment for humans.
- Automated scaffold sweep: a build/release gate that greps for these markers and fails the "production-ready" declaration if any remain unresolved.
- No agent may self-report "done/removed" without the sweep independently re-confirming zero markers — self-attestation from the same agent that introduced the mock is not sufficient evidence.

**Incorporation steps:**
1. Add a lint rule/CI step scanning for the scaffold marker pattern across the repo.
2. Require every agent-generated PR/commit to include a scaffold-marker diff (added/removed count) in its summary.
3. Track outstanding scaffold markers as an explicit backlog (ticket per marker), not an implicit TODO buried in code.
4. For IDE-driven builds specifically: instruct the agent up front (in the system/requirements prompt) to fetch from real integrations from the first step rather than defaulting to mock data "to look complete" — this is reported as the single highest-leverage prompt-level fix.

Source: documented failure pattern in agentic IDEs (Replit/Lovable/Bolt-class tools) and general hardcoding-as-code-smell literature.[web:11][web:15]

## 5. Layered Test-Fidelity Strategy (Stop Testing Against Fictional Mocks)

**Problem addressed:** Tests pass against hand-written mock LLM/tool responses that no real system would ever produce, so the pipeline is "verified" against a fictional universe, masking exactly the hardcoding problem in Section 4.

**Methodology — three-tier fixture hierarchy:**
- **Tier 1 — Stub fakes:** canned responses testing plumbing/control-flow/retry logic only. Fast, but never mistake this for testing real model/tool behavior.
- **Tier 2 — Recorded cassettes:** record real API/tool traffic once, replay deterministically (e.g., VCR-style). Captures actual response shape (schemas, streaming deltas, refusals). Re-record when providers change behavior.
- **Tier 3 — Live calls:** small, curated set hitting real providers/tools on a schedule (nightly/pre-merge), acting as a drift canary independent of what Tiers 1–2 say.

**Incorporation steps:**
1. Classify every existing test as Tier 1/2/3; flag any test whose "mock" is a hand-typed string with no link to a real captured response.
2. Introduce cassette recording for at least the critical path (the tool/API calls that most often get silently hardcoded).
3. Schedule Tier 3 live-call runs and diff against Tier 2 cassettes to catch model/tool drift before it becomes a hidden hardcoded workaround.

Source: dependency-injection/test-fidelity pattern for LLM and tool mocking.[web:12]

## 6. Trajectory-Level Observability (Design Requirement, Not Just a Tool)

**Problem addressed:** Without visibility into the full agent/layer trajectory, "one layer ignored another's output" is undiagnosable after the fact — this is an architectural requirement independent of which specific debugging tool you adopt.

**Methodology:**
- Every agent action, tool call, and inter-layer handoff must be logged with: sender, recipient, schema version, validation result (pass/fail/confidence), token cost, latency.
- Full trajectories (not just final outputs) must be persisted and replayable — replay is what turns "it broke somewhere" into "it broke at handoff k, because layer j returned an unvalidated mock."
- Debugging is modeled as a closed loop: Detect → Attribute (root-cause to the responsible layer/step) → Recover (propose a fix/rerun plan) → Rerun (validate the fix against the same trajectory), not as one-off log reading.

**Incorporation steps:**
1. Instrument the orchestration layer (LangGraph/AutoGen/custom) to emit structured trajectory events by default, not opt-in.
2. Require root-cause attribution to point to a specific step/layer/schema-version, not just "the pipeline failed."
3. Build or adopt a replay capability so a fix can be validated by rerunning from the exact failure checkpoint, not from the start.

Source: closed-loop debugging methodology (Detect/Attribute/Recover/Rerun) and interactive multi-agent debugging design goals.[web:3][web:5][web:7]

---

## Summary Table

| # | Methodology | Directly Solves |
|---|---|---|
| 1 | Explicit handoff contracts (typed, versioned, provenance+confidence) | Output of one layer not read/enforced by the next |
| 2 | Shared state layer (hot memory + event log + checkpointing) | Each phase re-deriving/mocking its own context |
| 3 | Verification/gating layer at handoff boundaries | Mocked/hallucinated values propagating downstream unchecked |
| 4 | Mock/hardcode lifecycle management with tagging + sweep | Hardcoded scaffolding surviving into "production" output |
| 5 | Three-tier test-fidelity hierarchy | Tests validated against fictional mocks, not real behavior |
| 6 | Trajectory-level observability (Detect/Attribute/Recover/Rerun) | Inability to diagnose which layer broke the chain |

These six are architectural policies to bake into pipeline/agent design from the start — none require a single specific product; each can be implemented with existing libraries (Pydantic, Redis, Kafka/Postgres, LangGraph Checkpointer, VCR-style recorders) plus the discipline described above.
