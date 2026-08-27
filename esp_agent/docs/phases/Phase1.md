# Phase 1 — Freeze the ESP Agentic Architecture

**Purpose:** establish the exact logical architecture, responsibilities, boundaries, interfaces, and technology decisions before building KB, tools, LangGraph, or integrations.

This phase is primarily **architecture + ownership + contract-definition work**, not feature implementation.

The Lead guideline already defines the major layers—Experience, Supervisor Agent, Asset Context, Data Services, Engineering Services, Knowledge Services, ML Services, Digital Twin and Governance. 
It also defines the Supervisor/specialist-agent organization and least-privilege model. 

---

# Phase 1 Structure

```text
PHASE 1 — ARCHITECTURE FREEZE
        │
        ├── Sprint 1.1 — Current-State / Repository Audit
        │
        ├── Sprint 1.2 — Target Architecture Definition
        │
        ├── Sprint 1.3 — Component & Responsibility Boundaries
        │
        ├── Sprint 1.4 — Integration / Service Boundary Definition
        │
        ├── Sprint 1.5 — Technology & Deployment Decisions
        │
        └── Sprint 1.6 — Architecture Review & Freeze
```

---

# Sprint 1.1 — Current-State / Repository Audit

### Objective

Understand what already exists in your half-built Agentic repository before designing the final structure around it.

### Tasks

| Task                  | Subtasks                                                                           |
| --------------------- | ---------------------------------------------------------------------------------- |
| Repository inventory  | Map folders, services, Python modules, prompts, graphs, tools, APIs, DBs, frontend |
| Runtime discovery     | Identify actual application entrypoints                                            |
| Agent discovery       | Find current Agent/Supervisor/router/planner/state implementation                  |
| Tool discovery        | List all existing tools and what they actually call                                |
| KB discovery          | Identify existing ingestion, vector DB, retrieval, metadata                        |
| LLM discovery         | Identify provider, client, model configuration, streaming/tool calling             |
| Integration discovery | Identify existing Advait/model/simulator/telemetry connections                     |
| Hardcode audit        | Find simulated telemetry, model outputs, fake KB answers, hardcoded rules          |
| Dependency audit      | Python libs, services, databases, external APIs                                    |
| Failure audit         | Run existing system and document broken paths                                      |
| Reuse assessment      | KEEP / REFACTOR / REPLACE / MISSING                                                |

### Subtasks in more detail

```text
Repository
 ├── entrypoints
 ├── agent runtime
 ├── LangGraph/custom orchestration?
 ├── tool registry
 ├── services
 ├── KB
 ├── LLM
 ├── frontend
 ├── databases
 └── deployment
```

### Deliverables

* As-is architecture diagram
* Repository component map
* Existing tool inventory
* Existing integration inventory
* Broken-component register
* Reusable-component register
* Technical debt register

### Prerequisites

* Repository access
* Working development environment
* Existing environment/configuration files

### Exit Criteria

Phase cannot move forward until:

* You know the actual execution path of the current Agent.
* Every existing tool has an identified purpose.
* Hardcoded/demo logic is identified.
* Existing reusable components are classified.
* Major unknowns are documented.

---

# Sprint 1.2 — Target Architecture Definition

### Objective

Convert the Lead guideline into **your actual ESP Agent architecture**.

The guideline's target architecture provides the source structure:

```text
Experience
Supervisor
Asset Context
Data Services
Engineering Services
Knowledge Services
ML Services
Digital Twin
Governance
```



### Task 1 — Define the top-level architecture

Freeze:

```text
                    EXPERIENCE
                        │
                 AGENT API / UI
                        │
                 SUPERVISOR AGENT
                        │
              LANGGRAPH ORCHESTRATION
                        │
        +---------------+----------------+
        │               │                │
   Specialist       Tools             Policy
    Agents
        │               │
        +-------+-------+
                │
         SERVICE LAYER
                │
     +----------+----------+
     │    │      │      │  │
   Asset Data Engineering KB ML Twin
```

### Task 2 — Freeze the Agent layers

Define:

```text
1. Experience Layer
2. Agent API
3. Supervisor
4. Objective Router
5. LangGraph State
6. Specialist Agents
7. Tool Registry
8. Tool Execution Layer
9. Evidence Pack
10. Context Builder
11. LLM Provider
12. Memory / Outcome Capture
13. Policy / Safety
14. Audit
15. Event Processor
```

### Task 3 — Define specialist agents

Based on the guideline:

* Well Performance
* Reliability
* Knowledge
* Optimization / Digital Twin
* Maintenance



For Phase 1, only define:

* responsibility
* inputs
* outputs
* allowed tools
* dependencies
* boundaries

Do **not** implement them yet.

### Task 4 — Decide deployment granularity

Freeze:

> Logical specialist agents ≠ mandatory separate containers.

For MVP:

```text
ONE Agent Platform
   ├── Supervisor
   ├── Specialist subgraphs
   ├── Objectives
   ├── Tools
   ├── Evidence
   └── Policies
```

This is an implementation recommendation, not a guideline requirement.

### Exit Criteria

You have:

* Target architecture diagram
* Component decomposition
* Specialist-agent boundaries
* Logical vs deployable component map
* No unexplained architecture boxes

---

# Sprint 1.3 — Component & Responsibility Boundaries

### Objective

Prevent ownership overlap between **your Agent team, ESP Model team, Advait/platform team and Engineering team**.

This is one of the most important Phase-1 activities.

The guideline explicitly assigns workstreams to ESP Engineering, Knowledge Engineering, ML Engineering, APM UX, MLOps/DevSecOps and QA/Validation. 

## Task 1 — Build RACI

| Component                | Agent team | ESP ML | Advait/platform | Engineering |
| ------------------------ | ---------: | -----: | --------------: | ----------: |
| Supervisor               |          R |      C |               I |           C |
| Objective layer          |          R |      C |               C |           C |
| KB                       |          R |      C |               C |         R/C |
| Asset context            |          C |      I |               R |           C |
| Telemetry                |          C |      C |               R |           I |
| Engineering calculations |          C |      I |               I |           R |
| Four ESP models          |          I |      R |               C |           C |
| Model API                |          C |      R |               C |           I |
| Digital Twin             |          C |      C |               I |           R |
| UI                       |        R/C |      C |               C |           C |
| Audit                    |          R |      C |               C |           C |

## Task 2 — Define ownership questions

You must explicitly answer:

* Who owns Asset Registry?
* Who owns tag mapping?
* Who owns historical model outputs?
* Who owns degradation calculations?
* Who owns Health/Fusion?
* Who owns engineering limits?
* Who owns pump curves?
* Who owns Digital Twin?
* Who owns client SOP authority?
* Who owns model events?

### Exit Criteria

Every major component has:

```text
Owner
Consumer
Source of truth
Interface
Versioning owner
Failure behavior
```

No component has ambiguous ownership.

---

# Sprint 1.4 — Integration / Service Boundary Definition

### Objective

Define **how components communicate**, before writing the integrations.

The guideline says ESP business logic shall be exposed through **APIs or MCP-compatible services** and should not be embedded in prompts. 

## Task 1 — Define service boundaries

Freeze these logical services:

```text
Asset Context Service
Telemetry/Historian Service
Event Service
Engineering Service
Knowledge Service
Model Adapter Service
Case/Maintenance Service
Digital Twin Service
Audit Service
```

## Task 2 — Define Agent tools

Example:

```text
get_asset_context()
get_live_snapshot()
get_history_window()
get_events_timeline()

calculate_operating_point()
calculate_tdh()
calculate_bep_deviation()
calculate_ror_margin()

get_anomaly()
get_failure_risk()
get_pump_degradation()

knowledge.search()
knowledge.search_faults()
case.search_similar()

run_what_if_frequency()

audit.record_advisory()
```

The guideline's Appendix B already provides corresponding illustrative contracts. 

## Task 3 — Decide communication mechanism

Freeze:

| Communication                         | Initial choice                 |
| ------------------------------------- | ------------------------------ |
| Agent → service                       | REST                           |
| Agent → MCP-capable selected services | Optional MCP                   |
| Frontend → Agent                      | HTTPS                          |
| Streaming UI                          | WebSocket/SSE                  |
| Model events                          | Event bus                      |
| Telemetry ingestion                   | Existing OT/platform mechanism |
| Internal same-process calls           | Python function                |

### Important

Do **not** implement MCP everywhere in Phase 1.

Phase 1 only decides:

> REST = default service interface
> MCP = optional targeted interface

The guideline permits “APIs or MCP-compatible services.” 

### Exit Criteria

For every service:

```text
service name
purpose
owner
input schema
output schema
transport
authentication
timeout
error model
versioning
```

are documented.

---

# Sprint 1.5 — Technology & Deployment Decisions

### Objective

Freeze the implementation technology without prematurely building everything.

## Task 1 — Agent stack

Recommended:

```text
Python
LangGraph
Pydantic
FastAPI where service is owned by us
```

**LangGraph is an implementation recommendation**, not mandated by the guideline.

## Task 2 — LLM architecture

Guideline says:

* local high-throughput inference
* vLLM/SGLang
* OpenAI-compatible API
* structured outputs/tool calling
* local models
* Qwen baseline, but not architectural lock-in. 

So freeze:

```text
Agent
 ↓
LLM Provider Interface
 ↓
OpenAI-compatible local endpoint
 ↓
vLLM/SGLang
```

## Task 3 — Data/KB stack

Recommended:

```text
PostgreSQL
pgvector
MinIO/S3
Redis
```

These are **implementation recommendations**, not Lead requirements.

## Task 4 — Deployment model

Freeze MVP as:

```text
Agent Platform Container
     +
Local LLM Runtime
     +
Required Services
     +
Infrastructure Containers
```

Do **not** create a container per specialist Agent automatically.

### Exit Criteria

Technology Decision Record exists for:

* Agent framework
* LLM runtime
* Service framework
* Database
* Vector DB
* Object store
* Event bus
* Deployment
* Observability

---

# Sprint 1.6 — Architecture Review & Freeze

### Objective

Get the architecture to a state where development teams can begin implementation without redesigning the foundation every week.

## Task 1 — Architecture review

Review:

```text
System architecture
        ↓
Agent architecture
        ↓
Multi-agent architecture
        ↓
Service architecture
        ↓
Tool architecture
        ↓
Data architecture
        ↓
Security architecture
        ↓
Deployment architecture
```

## Task 2 — Traceability review

Every major architecture choice should be classified:

```text
GUIDELINE REQUIREMENT
IMPLEMENTATION RECOMMENDATION
TEAM DECISION
OPEN QUESTION
```

## Task 3 — Freeze open issues

Anything unresolved becomes:

```text
Architecture Decision Record
```

with:

```text
ADR-ID
Decision
Context
Options
Chosen option
Reason
Owner
Date
Impact
```

---

# Phase 1 Final Deliverables

At the end of Phase 1, you should have:

| Deliverable                   | Required |
| ----------------------------- | -------: |
| As-is architecture            |      Yes |
| Target architecture           |      Yes |
| Granular Agent diagram        |      Yes |
| Multi-agent diagram           |      Yes |
| Service-layer diagram         |      Yes |
| Tool-layer diagram            |      Yes |
| Data-flow diagram             |      Yes |
| Deployment diagram            |      Yes |
| Responsibility/RACI matrix    |      Yes |
| Service inventory             |      Yes |
| Tool inventory                |      Yes |
| External dependency matrix    |      Yes |
| Technology decision record    |      Yes |
| Security boundary document    |      Yes |
| Architecture Decision Records |      Yes |
| Guideline traceability matrix |      Yes |
| Open-questions register       |      Yes |

---

# Phase 1 Exit Gate

Phase 1 is **DONE only when** this statement is true:

> “Another developer can look at the architecture documents and implement the next phase without asking what the Agent, specialist agents, services, tools, data sources or external-team responsibilities are supposed to be.”

And specifically:

```text
WHO owns what?
          ✓

WHERE does data come from?
          ✓

WHO calls whom?
          ✓

WHAT is a tool?
          ✓

WHAT is a service?
          ✓

WHAT does the Agent see?
          ✓

HOW do components communicate?
          ✓

WHAT is LangGraph responsible for?
          ✓

WHAT is the LLM responsible for?
          ✓

WHAT remains outside our team?
          ✓

WHAT is the source of truth?
          ✓

WHAT is mandatory from Guidelines.pdf?
          ✓

WHAT is our implementation choice?
          ✓
```

### Phase 1 dependency

You **do not need the four ESP models finished** to complete Phase 1.

You **do need their intended interface/ownership information** sufficiently defined to create the integration contracts later.

The guideline's architecture explicitly separates ML Services from the Supervisor/Engineering/Knowledge layers, which supports this contract-first approach. 

**Phase 1 output → Phase 2 starts:**
`Frozen Agentic Architecture + Ownership + Service Boundaries + Integration Contracts + Technology Decisions.`
