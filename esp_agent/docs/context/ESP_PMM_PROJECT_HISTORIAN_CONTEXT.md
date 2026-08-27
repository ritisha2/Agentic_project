# ESP-PMM / ESP Agentic AI Project — Complete Context Preservation Document

**Last updated:** 24 August 2026

## A. PROJECT OVERVIEW

### A1. Project identity
This project is an ESP Asset Performance Monitoring & Management (ESP-PMM) system associated with the ADVAIT/EPR platform context. The source deck frames the work as:

> Equipment domain → data model → AI advisor

The deck’s mission is to turn ESP data into actionable intelligence with physics, evidence and operational discipline.

### A2. Current ownership boundary — IMPORTANT
The current, corrected understanding is:

**Another team owns the four ESP AI model layers:**
1. Rule Engine
2. Anomaly Detection
3. Failure Prediction
4. Fault Classification

**The user owns the Agentic AI layer:**
- LLM integration
- RAG / retrieval
- tool calling
- orchestration
- consumption of live telemetry
- consumption of model outputs
- evidence/grounding
- alert explanation
- safe recommendation generation
- operational reporting
- Agent UI/integration

The four predictive models are not to be rebuilt by the user unless the scope is explicitly changed.

### A3. Core architecture
```text
Existing ESP Simulator
        |
        | live/historical telemetry API
        v
Telemetry / Asset API
        |
        +----------------------------+
        |                            |
        v                            v
Other Team's ESP AI Models      Your Agentic System
        |                            |
        | model outputs              | LLM + RAG + tools
        v                            |
Model Output API / Events            |
        |                            |
        +-------------+--------------+
                      |
                      v
               Agent Orchestrator
                      |
        +-------------+-------------+
        |             |             |
        v             v             v
   Live data     Model outputs   Knowledge Base
        |             |             |
        +-------------+-------------+
                      |
                      v
                     LLM
                      |
                      v
            Evidence-backed answer
                      |
                      v
                 Dashboard
```

### A4. Current state
- ESP simulator: already exists.
- Simulator generates multiple ESP/well assets and scenarios/faults.
- Live telemetry for development is expected through an API.
- Predictive model implementation belongs to another team.
- Agentic architecture is defined conceptually but integration contracts are not yet frozen.
- Knowledge base has a generic 12-category foundation; ESP-specific categories still need to be added.
- The key next engineering step is to define the **Telemetry API Contract**, **Model Output Contract**, **Agent Tool Schemas**, and **Knowledge Retrieval Contract**.

---

## B. TIMELINE / VERSION HISTORY

### Phase 1 — Initial PDF study and full ESP-PMM interpretation
The user initially asked for an in-depth, page-by-page study of the ESP-PMM PDF and instructions for building an ESP Model Dashboard that could ingest data from an existing simulator.

The initial interpretation was a full stack:
```text
Simulator
→ Ingestion/API
→ Canonical ESP Data Model
→ Physics/Feature Engine
→ Rule Engine
→ ML Models
→ Dashboard
→ AI Assistant
```

Key ideas:
- simulator as synthetic source
- backend/API between simulator and frontend
- canonical ESP schema
- asset registry
- tag binding
- data quality
- engineering calculations
- pump curves/ROR
- rule engine
- anomaly detection
- failure prediction
- fault classification
- model validation against simulator ground truth
- evidence-backed assistant

### Phase 2 — Canonical ESP data model
A canonical data contract was proposed so the simulator’s internal tag names would map to standardized ESP variables.

Typical fields discussed:
- timestamp
- well_id
- esp_id
- flow
- PIP
- PDP
- WHP
- frequency
- current
- voltage
- motor temperature
- intake temperature
- vibration
- water cut
- GOR
- API
- BHT
- reservoir pressure
- pump model
- stage count
- BEP
- ROR
- motor HP
- set depth

Decision: frontend should visualize backend/authoritative calculations, not become the source of physics logic.

### Phase 3 — Ground-truth separation
A major principle was introduced:
- simulator knows the scenario/fault/failure ground truth;
- inference does not receive the ground truth;
- ground truth is used only for training/evaluation/validation.

```text
Simulator
 ├── Observed telemetry → inference
 └── Ground truth       → validation only
```

This is required to avoid leakage.

### Phase 4 — Rule engine before ML
The first model-stack interpretation recommended deterministic engineering rules before ML.

Rules discussed:
- outside ROR
- TDH deviation
- pump-curve deviation
- high motor temperature
- overload
- underload
- voltage/current imbalance
- excessive starts/stops
- PIP abnormality
- PDP abnormality
- flow abnormality
- multi-signal trip risk

The ESP deck explicitly calls Rule Engine work “known physics and operating limits,” including thresholds, state machines and pump-curve checks.

### Phase 5 — Dataset requirements
Different data needs were distinguished:
- Rule Engine → engineering/design knowledge
- Anomaly Detection → normal multivariate time-series
- Fault Classification → labelled fault data
- Failure Prediction → longitudinal degradation-to-failure histories

The existing simulator was identified as particularly useful for controlled labelled scenarios and failure trajectories.

### Phase 6 — Public dataset search
The conversation identified and discussed:
- Petrobras 3W Dataset 2.0.0
- ESPset v3
- OIL-039 sample
- OIL-038 sample
- AI4EU pump dataset

Use expectations:
- 3W → anomaly/process-event work
- ESPset → real ESP vibration fault classification
- OIL-039 → synthetic prognostics/RUL pipeline
- OIL-038 → synthetic failure/maintenance/RCA pipeline
- AI4EU → optional supplementary pump anomaly work

Important correction: these public datasets do not replace the existing simulator, and the synthetic datasets must not be presented as real ESP operational ground truth.

### Phase 7 — Antigravity master implementation prompt
A long prompt was created for Google Antigravity covering:
- repository setup
- dataset acquisition
- data profiling
- canonical schema
- feature engineering
- rule engine
- anomaly detection
- fault classification
- failure prediction
- PMM fusion
- simulator integration
- APIs
- dashboard
- validation
- model registry
- testing
- MLOps

**This prompt is now outdated in one important respect:** it assumed the user would own and build the four model layers.

### Phase 8 — Transcript review
The user uploaded a noisy technical meeting transcript. Important ideas extracted:
- simulator scenarios already exist
- ground truth must remain simulator-side
- live production data will be queried from asset APIs
- asset IDs are important
- system should discover/register/refresh asset lists
- the model engine processes assets
- dashboard shows model outputs
- the Agent is built on the outputs
- alerts/alarms should be explainable by the Agent
- knowledge base must become operational/real rather than purely synthetic
- knowledge should come from manufacturers, datasheets, manuals, operational data and domain expertise
- Agent has objectives and needs live data + knowledge
- the system should support future expansion to more equipment classes

### Transcript correction
The user explicitly corrected a transcription mistake:
- “GST” should actually be **EPR**.

Other transcript acronyms such as ASP/USP/BSP/CSP/SP were noisy speech-to-text artifacts and should not be assumed to represent separate technologies without confirmation.

### Phase 9 — Major scope clarification
The user clarified:
- live telemetry comes from simulator API
- the ESP AI model part is handled by another team
- the Agentic part is handled by the user
- user has limited knowledge of the model internals
- LLMs are not used in the four predictive model layers
- the LLM is only for the Agentic layer
- fetching model outputs can be through any reasonable mechanism: API, event, database, function, etc.

This changed the current architecture from “user builds entire ML stack” to “user builds Agent over other team’s model services.”

### Phase 10 — End-to-end call-flow examples
A full simulation of a client interaction was discussed.

Example:
User asks:
> “What is the current status of ESP-007?”

Flow:
```text
Client
→ Agent API
→ LLM determines required information
→ get_asset_status(ESP-007)
→ Telemetry API
→ Simulator
→ telemetry response
→ LLM
→ answer
```

Another example:
> “Why is ESP-007 showing a warning?”

Agent retrieves:
- current telemetry
- active rules/alerts
- anomaly result
- fault classification
- failure prediction
- engineering knowledge

LLM synthesizes an evidence-backed answer.

### Phase 11 — Agentic architecture refined
The Agent should not be a generic chatbot.

It should:
1. identify objective
2. identify asset
3. select tools
4. retrieve live data
5. retrieve model outputs
6. retrieve relevant knowledge
7. reason over the context
8. validate evidence
9. respond with confidence/evidence/escalation

Two modes:
- user-driven question answering
- event-driven alert explanation

### Phase 12 — Knowledge Base evaluation
The user presented a 12-category AIConnex KB.

Original 12:
1. Platform Documentation
2. Industrial Domain Knowledge
3. Equipment & Asset Knowledge
4. Dataset Documentation
5. Standards & Specifications
6. Tenant Knowledge
7. Historical Project Knowledge
8. ML Methodology Knowledge
9. Algorithm / Model Documentation
10. Compiler / Parser Documentation
11. Business Glossary
12. Units / Feature Semantics

Conclusion: these are a strong general platform foundation but not enough for a domain-specific ESP Agent.

Recommended additions:
13. ESP OEM / Manufacturer Knowledge
14. ESP Physics & Calculation Knowledge
15. ESP Fault & Troubleshooting Knowledge
16. Alert / Exception / Action Playbooks
17. Model Output / Model Semantics Knowledge
18. API / Data Contract Knowledge
19. Historical Asset / Maintenance / Failure Knowledge
20. Evidence / Provenance Knowledge
21. Agent Objective / Question Library

Critical distinction:
- static knowledge → KB
- dynamic facts → tools/APIs
- predictive results → model service
- reasoning/synthesis → LLM

---

# C. REQUIREMENTS & GOALS

## C1. Functional requirements

### Live and historical data
- consume simulator telemetry through API
- support historical queries
- support asset discovery
- support asset-level querying
- later replace simulator provider with EPR/Advait production API

### Model integration
- consume other team’s model outputs
- do not depend on internal algorithms
- support current and historical results where available
- support alert/event ingestion
- preserve timestamp/model version/asset ID
- provide a stable model adapter

### Agentic behavior
The Agent must be capable of:
- observing asset state
- checking data quality
- checking trends
- checking exceptions
- explaining anomalies
- diagnosing likely causes using model evidence
- explaining alerts/alarms
- explaining failure risk
- answering historical questions
- generating safe operational next steps
- generating shift/exception notes
- supporting operator feedback

### Evidence and trust
Every response should include:
- confidence/uncertainty
- evidence
- relevant tags/values
- relevant calculations
- knowledge source/procedure
- escalation criteria
- timestamp

### Safety
Never:
- invent sensor values
- invent model predictions
- recommend unsafe control changes
- suppress alarms
- hide uncertainty
- hide evidence
- override procedures
- directly control the ESP without approved human-in-the-loop workflow

## C2. Non-functional
- reproducible
- versioned
- explainable
- testable
- auditable
- traceable
- configurable
- API-driven
- no hard-coded outputs
- no scenario-label leakage
- scalable beyond one asset

---

# D. ARCHITECTURE / APPROACH

## D1. Four analytical models are external dependencies
Treat the model team as a black box.

Conceptually:
```text
Agent
  |
  +--> model_provider.get_current_output(asset_id)
```

Underneath this could use:
- REST
- POST inference API
- gRPC
- database
- message broker
- event bus
- same-process function

The Agent must not care.

## D2. Telemetry provider abstraction
Use:
```text
telemetry_provider.get_live_data(asset_id)
telemetry_provider.get_history(asset_id, start, end)
```

Development:
```text
Simulator API
```

Future:
```text
EPR/Advait Asset API
```

## D3. Knowledge provider
Use:
```text
knowledge_provider.search(query, metadata_filters)
```

Return:
- text
- source
- title
- manufacturer
- page/section
- version
- date
- equipment
- chunk ID

## D4. Agent tools
Potential tools:
```text
get_asset_list()
get_asset_details(asset_id)
get_live_telemetry(asset_id)
get_historical_telemetry(asset_id, start, end)
get_current_model_outputs(asset_id)
get_historical_model_outputs(asset_id, start, end)
get_active_alerts(asset_id)
get_rule_events(asset_id)
get_anomaly_status(asset_id)
get_fault_diagnosis(asset_id)
get_failure_prediction(asset_id)
get_maintenance_history(asset_id)
get_engineering_configuration(asset_id)
get_operating_envelope(asset_id)
search_knowledge_base(query, filters)
generate_shift_note(...)
```

## D5. Two agent modes

### User-driven
```text
User
→ Agent
→ intent/objective
→ tools
→ data/model/KB
→ LLM
→ answer
```

### Event-driven
```text
Model event
→ Agent
→ context retrieval
→ LLM
→ explanation/notification
→ dashboard
```

---

# E. KEY IDEAS & INSIGHTS

## E1. Model vs Agent
Predictive models answer:
> What is happening / what is predicted?

Agent answers:
> What does it mean, why does it matter, what evidence supports it, and what safe next step should be considered?

## E2. RAG is not enough
The Agent needs:
- RAG
- live telemetry
- historical telemetry
- model outputs
- engineering context
- maintenance history

## E3. KB vs Tools
KB:
- OEM manuals
- ESP fault definitions
- troubleshooting
- physics concepts
- procedures
- standards
- model semantics
- API documentation

Tools:
- current temperature
- current flow
- current anomaly score
- failure risk
- active alerts
- historical data
- maintenance history

## E4. Ground truth is validation-only
Scenario/fault/failure labels stay on simulator side and must not leak into inference.

## E5. Agent needs explicit objectives
Example objectives:
1. asset status
2. asset information
3. performance analysis
4. alert explanation
5. fault diagnosis
6. failure risk
7. historical investigation
8. performance improvement
9. shift report
10. exception report

---

# F. IMPLEMENTATION DETAILS

## F1. Proposed telemetry contract
Illustrative:
```json
{
  "timestamp": "...",
  "asset_id": "ESP-007",
  "well_id": "WELL-007",
  "flow_bpd": 2200,
  "pip_psi": 850,
  "pdp_psi": 2450,
  "whp_psi": 420,
  "frequency_hz": 52,
  "current_a": 68,
  "motor_temperature_c": 155,
  "vibration": 4.2
}
```

## F2. Proposed model-output contract
Illustrative:
```json
{
  "asset_id": "ESP-007",
  "timestamp": "...",
  "anomaly": {
    "status": "ANOMALOUS",
    "score": 0.91
  },
  "fault_classification": {
    "fault": "MOTOR_OVERHEATING",
    "confidence": 0.87
  },
  "failure_prediction": {
    "risk_1h": 0.08,
    "risk_24h": 0.31,
    "risk_7d": 0.74,
    "rul_hours": 96
  },
  "rules": {
    "severity": "WARNING",
    "triggered_rules": ["MOTOR_TEMP_MARGIN_LOW"]
  }
}
```

These examples are architectural placeholders, not confirmed contracts.

## F3. Model-team questions
Ask:
- how to invoke inference?
- request schema?
- response schema?
- current/historical outputs?
- real-time events?
- model version?
- confidence semantics?
- evidence?
- failure handling?
- stale-data behavior?
- latency?

## F4. Example current-status request
User:
> What is the current status of ESP-007?

Agent:
1. identify asset
2. call telemetry
3. optionally call model output
4. assemble context
5. LLM responds
6. attach evidence

## F5. Example warning explanation
User:
> Why is ESP-007 showing a warning?

Agent retrieves:
- telemetry
- active rule/alert
- anomaly
- fault
- failure risk
- relevant engineering source

Then LLM explains it.

## F6. Example historical investigation
User:
> Why did ESP-007 performance drop yesterday?

Agent retrieves:
- historical telemetry
- historical model outputs
- alerts/rules
- maintenance/events
- knowledge as needed
Then constructs an evidence timeline.

---

# G. ITERATIONS & REFINEMENTS

| Earlier assumption | Current refined interpretation | Why |
|---|---|---|
| User builds all four models | Other team builds four models | Explicit user clarification |
| LLM could support model stack generally | LLM only in Agentic layer | User requirement |
| Agent as dashboard chatbot | Agentic operational copilot | Deck + transcript |
| Direct simulator integration | Telemetry provider/API abstraction | Production compatibility |
| RAG alone | RAG + tools + model APIs | Need live/current context |
| Generic 12-category KB | 21-category ESP Agent KB | Domain-specific operational needs |
| Live telemetry could be KB context | Live telemetry must be tool/API data | Freshness and accuracy |
| Model implementation important to user | Model interface/semantics important | Ownership boundary |
| Static dashboard primarily | Dynamic dashboard backed by real model/API outputs | No hardcoding requirement |

---

# H. OPEN PROBLEMS / PENDING WORK

1. Exact simulator API contract.
2. Exact model team API/event contract.
3. Model output schemas and semantics.
4. Asset discovery API.
5. Historical model output access.
6. Alert/event transport.
7. Knowledge base ingestion pipeline.
8. Actual ESP OEM/document corpus.
9. Evidence/provenance schema.
10. Agent objective/question library.
11. Agent evaluation set.
12. Persistent vs session memory.
13. Exact dashboard ownership/integration boundary.
14. Production EPR/Advait API contract.
15. Authentication/authorization for tools.
16. Data freshness/timeout policies.
17. Human approval workflow.
18. Agent audit/tracing storage.
19. Model-result caching strategy.
20. Final database/time-series/vector architecture.

---

# I. USER PREFERENCES & EXPECTATIONS

- Precision over fluff.
- Detailed technical structure.
- Explicit assumptions and uncertainty.
- No fabricated metrics or outputs.
- No hard-coded values.
- Implementation plans should be comprehensive but executable in phases.
- Preserve prior decisions rather than restarting from scratch.
- Prefer reusable abstractions.
- Wants end-to-end concrete examples showing who calls whom.
- Wants the final system to behave as a real project rather than a static mock.
- Wants project continuity preserved across new chats.

---

# J. IMPORTANT CONTEXT THAT MUST NOT BE LOST

1. **User does not own the four ESP predictive models.**
2. **User owns the Agentic/LLM layer.**
3. **Simulator supplies live telemetry through API during development.**
4. **EPR is the corrected integration/platform terminology where transcript transcription had “GST”.**
5. **Transcript acronym variants are unreliable; do not treat ASP/USP/BSP/CSP/SP as confirmed distinct components.**
6. **LLM is only used in the Agentic layer.**
7. **Model outputs can come through API, event, database, etc.**
8. **Use adapter interfaces to hide model implementation.**
9. **Agent consumes model outputs; it does not reimplement the predictive models.**
10. **Ground truth must stay out of inference.**
11. **KB should contain static knowledge; tools should provide dynamic facts.**
12. **Agent must have explicit objectives.**
13. **Agent must cite evidence and provide confidence/escalation.**
14. **No unsafe autonomous action.**
15. **The deck’s assistant is a RAG + tool-calling + evidence-card operational copilot.**
16. **The final user interaction should support questions, alerts, explanations, recommendations and reports.**

---

# K. QUICK RESTART CONTEXT

Paste this block into a new chat:

> I am building the **Agentic AI layer for an ESP-PMM platform**.
>
> An existing ESP simulator creates multiple wells/assets and fault scenarios. Live telemetry for development will come from the simulator through an API. Simulator ground truth must remain hidden from inference and be used only for validation.
>
> Another team owns the four ESP AI model layers: **Rule Engine, Anomaly Detection, Failure Prediction, Fault Classification**. I do NOT need to build those models. I need to consume their outputs. The internal algorithms are a black box to me. The model team may expose outputs through REST API, gRPC, database, event broker, or another mechanism. I need a stable `ModelProvider` adapter.
>
> I own the **Agentic layer**, which uses **LLM + RAG + tool calling**. No LLM is required inside the predictive models. The Agent should retrieve live telemetry, historical telemetry, model outputs, alerts, maintenance history, engineering context and knowledge, then reason over them and produce evidence-backed operational responses.
>
> The deck explicitly says the assistant is an **evidence-backed operational copilot**, not a chatbot: it should observe asset state/data quality/trends/exceptions, diagnose, explain, recommend safe next steps, and document reports/shift notes. Every answer needs confidence, evidence and escalation criteria.
>
> Important architecture:
>
> ```text
> Simulator API
>    ↓
> Telemetry Provider
>    ↓
> AI Models / Model Output API or Events
>    ↓
> Agent Tools
>    ├── live telemetry
>    ├── history
>    ├── model outputs
>    ├── alerts/rules
>    ├── maintenance
>    ├── engineering calculations
>    └── knowledge search
>    ↓
> Agent Orchestrator
>    ↓
> LLM
>    ↓
> Evidence-backed answer
>    ↓
> Dashboard
> ```
>
> The KB should have the original 12 generic categories plus ESP-specific categories:
> OEM/manufacturer docs, ESP physics/calculations, ESP fault/troubleshooting knowledge, alert/action playbooks, model-output semantics, API/data contracts, asset maintenance/history, evidence/provenance, and agent objectives/question library.
>
> Static knowledge belongs in the KB; live/current data must come from tools/APIs.
>
> Key example:
>
> User: “Why is ESP-007 showing a warning?”
>
> Agent:
> 1. identifies ESP-007
> 2. gets current telemetry
> 3. gets active alerts
> 4. gets anomaly/fault/failure model outputs
> 5. searches relevant ESP engineering knowledge
> 6. combines evidence
> 7. LLM explains why
> 8. gives safe next step + escalation
>
> Do not hard-code predictions. Do not invent telemetry. Do not leak simulator ground truth. Do not make the Agent directly control the ESP.
>
> The next concrete deliverable should be the **Model Output Contract + Telemetry Tool Contract + Agent Tool Schemas + Knowledge Retrieval Contract**, followed by the first working vertical slice.
