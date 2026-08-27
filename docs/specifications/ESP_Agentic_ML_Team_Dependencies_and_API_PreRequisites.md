# ESP APM Agentic Layer — ML Team Dependency & API Pre-Requisite Matrix

**Revision:** 1.0  
**Date:** 25 Aug 2026  
**Purpose:** Define the technical dependencies of the Agentic layer on the ESP Model/ML team, what contracts must be agreed, what can be mocked while ML is not ready, and what integration cautions apply.

## 1. Scope Boundary

| Area | ESP Model/ML Team | Agentic Team |
|---|---|---|
| Deterministic rules | Build/operate rule engine | Consume and explain |
| Multivariate anomaly | Build/operate anomaly model | Consume score/contributors/baseline |
| Failure/degradation/RUL | Build models and calibration | Consume risk, RUL, drivers |
| Thermal/gas/vibration models | Build specialist models | Consume outputs |
| Pattern/fault detection | Computational detection/classification | Explain using KB/history |
| Model registry/versioning | Own | Consume metadata |
| Asset registry | Advait/client platform | Consume; cache only |
| Live telemetry | OT/Data/Platform | Consume via tools |
| KB/RAG |  | Own |
| Objectives/planning |  | Own |
| Tool orchestration |  | Own |
| Evidence/context |  | Own |
| LLM |  | Own |
| Safety/policy orchestration | Shared with Engineering/OT | Own Agent side |
| Dashboard | Shared | Consume normalized outputs |

The latest guideline explicitly separates **Supervisor Agent**, **Data Services**, **Engineering Services**, **Knowledge Services**, **ML Services**, **Digital Twin**, and **Governance**. It also states that business logic should be exposed through APIs or MCP-compatible services rather than embedded in prompts.

## 2. Critical Dependency Matrix

| Priority | Dependency | Required from ML team | Why Agent needs it | Can build before ML is ready? |
|---|---|---|---|---|
| P0 | Model output schema | Versioned JSON/OpenAPI schema | Stable parsing | Yes — mock |
| P0 | Model API/service | REST/gRPC/MCP-compatible or equivalent | Runtime predictions | Yes — mock adapter |
| P0 | asset_id/well_id mapping | Stable IDs | Correlate every result to ESP | Yes — simulator |
| P0 | Timestamp + input window | `timestamp`, `window_start`, `window_end` | Explain time context | Yes |
| P0 | Model/feature version | `model_version`, `feature_version` | Audit/reproducibility | Yes |
| P0 | Data quality | quality/coverage/status | Prevent unsafe conclusions | Yes |
| P0 | Confidence semantics | Probability/confidence definition | Explain uncertainty | Yes, but semantics must be fixed |
| P0 | Anomaly result | score, start time, contributors, baseline | Abnormality explanation | Yes — fixture |
| P0 | Failure result | horizon probabilities, drivers, calibration | Future risk answers | Yes — fixture |
| P0 | Fault/pattern result | pattern/fault/confidence/alternatives | Diagnosis | Yes — fixture |
| P0 | Historical results | Queryable past predictions/events | RCA and trend questions | Yes — local fixture DB |
| P1 | Forecast/threshold crossing | Forecast trajectory + uncertainty | Explain likely future state | Yes |
| P1 | Health result | score/state + drivers | Unified health display | Yes |
| P1 | Model events | Alert/risk-change events | Proactive Agent | Yes — replay |
| P2 | Drift/calibration | drift + calibration metadata | Production governance | Later |
| P2 | Training lineage | dataset/version/features | Audit | Later, production gate |
| P2 | Benchmark report | holdout metrics | Release governance | Later |

## 3. Minimum Model Contract

Every inference result should carry:

| Field | Requirement |
|---|---|
| `asset_id` | Mandatory |
| `well_id` | Mandatory |
| `timestamp` | Mandatory |
| `input_window_start/end` | Mandatory for time-series |
| `model_id` | Mandatory |
| `model_version` | Mandatory |
| `feature_version` | Mandatory |
| `status` | `VALID`, `DEGRADED`, `UNAVAILABLE`, etc. |
| `data_quality` | Mandatory |
| `prediction` | Actual result |
| `confidence/probability` | Where applicable |
| `dominant_drivers` | Strongly recommended |
| `evidence_refs` | Strongly recommended |
| `warnings/errors` | Mandatory where applicable |

Never expose a bare value such as `0.73` without semantics.

## 4. Anomaly Contract

The guideline specifies multivariate anomaly inputs such as PIP, PDP, WHP, flow, current, frequency, temperatures and vibration.

| Output | Example |
|---|---|
| status | `ANOMALOUS` |
| anomaly_score | `0.84` |
| anomaly_start | timestamp |
| input_window | last 6h |
| baseline_id | `BASELINE-PUMPX-V3` |
| contributors | motor_temp, current, PIP |
| model_version | `anomaly-2.1` |

## 5. Failure / Degradation Contract

| Output | Requirement |
|---|---|
| 24h risk | Required |
| 72h risk | Required by guideline |
| 7d risk | Required |
| 30d risk | Required where model supports |
| confidence | Required |
| dominant drivers | Required |
| calibration status | Production requirement |
| RUL | When available |
| forecast trajectory | Recommended |
| threshold-crossing time | Recommended |

Do not treat failure probability, RUL, forecast and anomaly score as interchangeable.

## 6. Pattern / Fault Contract

The current meeting and guideline make computational pattern matching part of the model layer. The Agent should consume it.

```json
{
  "pattern_id": "PAT-006",
  "pattern_name": "Possible Gas Interference",
  "match_confidence": 0.91,
  "fault_class": "GAS_INTERFERENCE",
  "fault_confidence": 0.87,
  "contributors": ["flow_instability", "current_instability", "PIP/PDP_instability"],
  "alternatives": [{"fault": "INTAKE_RESTRICTION", "confidence": 0.18}],
  "model_version": "fault-v3.2"
}
```

### Scope

| Function | ML Team | Agentic Team |
|---|---:|---:|
| Detect pattern from telemetry | Yes | No |
| Compute match score | Yes | No |
| Train classifier | Yes | No |
| Explain pattern |  | Yes |
| Retrieve supporting documentation |  | Yes |
| Retrieve similar cases |  | Yes |
| Map pattern to playbook |  | Yes |

## 7. Health Index

If the ML team owns health aggregation, require:

| Field | Example |
|---|---|
| health_index | `82.4` |
| health_state | `WATCH` |
| drivers | repeated deviations, anomaly rise |
| component_scores | rule/anomaly/failure/fault |
| health_model_version | `health-1.2` |

The LLM must never invent a health formula.

## 8. Historical Model Access

The Agent needs historical model results for questions such as “what happened before the trip?”

Recommended interface:

```http
GET /api/v1/esps/{asset_id}/model-history?start=...&end=...
```

Return timestamped results and model versions, not only the latest state.

## 9. Live Data Dependency

Every telemetry value supplied to the Agent must include:

| Field | Required |
|---|---:|
| asset_id | Yes |
| tag/parameter | Yes |
| value | Yes |
| unit | Yes |
| timestamp | Yes |
| source | Yes |
| quality | Yes |

The guideline explicitly says that missing fields require confidence reduction or rejection rather than silent inference.

## 10. Data Quality Prerequisites

| Check | Required |
|---|---:|
| freshness/communication | Yes |
| frozen/stuck values | Yes |
| spikes/outliers | Yes |
| impossible ranges | Yes |
| unit mismatch | Yes |
| timestamp alignment | Yes |
| cross-sensor consistency | Yes |
| sensor drift/baseline shift | Yes |
| missing samples/compression | Yes |

Default history windows from the guideline:

`15m, 1h, 6h, 24h, 7d, 30d, since startup, since last intervention`.

## 11. Engineering Services Dependency

The Agent also depends on deterministic engineering services, separate from ML:

| Service group | Examples |
|---|---|
| Hydraulic/well | `calculate_ipr`, `calculate_pwf`, `calculate_pip`, `calculate_pdp`, `calculate_tdh` |
| Pump/gas | `get_pump_curve`, `calculate_operating_point`, `calculate_bep_deviation`, `calculate_ror_margin`, `calculate_free_gas_at_intake` |
| Electrical/reliability | `calculate_motor_load`, `calculate_voltage_drop`, `calculate_current_imbalance`, `calculate_runtime`, `calculate_availability`, `estimate_degradation_rate` |

The LLM selects these tools but must not recreate their calculations free-form.

## 12. Asset Configuration Dependency

The Agent must identify exact installed configuration before answering operating questions.

Required context includes:

| Domain | Required examples |
|---|---|
| Well | well ID, MD/TVD, casing/tubing, pump setting depth, reservoir P/T, PI/IPR |
| Fluid | API/SG, water cut, GOR/GLR, PVT, viscosity, solids, scale/corrosion |
| ESP | pump model/stages/BEP/ROR/curves, motor ratings, gas handler, protector, cable, VSD |

Asset registry should remain Advait/client system of record; your Agent should consume it through an Asset Service/cache.

## 13. Digital Twin Dependency

For what-if questions, expose a deterministic service such as:

```http
POST /engineering/what-if/frequency
```

Inputs may include asset_id and target frequency.

Outputs should include:
- predicted production
- PIP/PDP
- pump head
- BEP/ROR position
- motor load
- gas fraction
- thermal/electrical/reliability margins
- constraints

The guideline requires production benefit and corresponding reliability margin changes.

## 14. API / Transport Recommendation

| Use case | Preferred transport |
|---|---|
| Agent gets current model state | REST/gRPC/MCP |
| Agent gets history | REST/gRPC |
| Proactive model event | Kafka/RabbitMQ/Redis Streams or equivalent |
| Dashboard live stream | WebSocket/SSE |
| Model artifacts | Object storage |
| Audit | DB/event store |

**WebSocket is not a mandatory dependency for the Agent core.** The Agent should have request/response access to authoritative services and optionally consume event streams for proactive surveillance.

## 15. Failure / Unavailability Behavior

Never convert model failure into a false healthy state.

Bad:
`model timeout -> risk = 0`

Correct:

```json
{
  "status": "UNAVAILABLE",
  "reason": "MODEL_TIMEOUT",
  "last_valid_result_timestamp": "...",
  "confidence": null
}
```

Agent response:
“Failure-risk model is currently unavailable; no current failure probability is being asserted.”

## 16. Security / Network Prerequisites

The guideline is offline-first and advisory-only.

Required:
- local/on-prem LLM inference
- network segmentation between OT read interfaces and AI services
- RBAC at every tool boundary
- explicit tool allowlist
- separate read-only credentials from future write credentials
- no direct VSD/PLC/ESD control in initial releases
- encrypted storage/transport where required

## 17. Model Governance Prerequisites

Before production integration, require:

| Artifact | Required |
|---|---:|
| model card | Yes |
| API/OpenAPI schema | Yes |
| model version | Yes |
| feature version | Yes |
| feature definition | Yes |
| label taxonomy | Yes |
| probability semantics | Yes |
| calibration report | Probability models |
| benchmark/holdout report | Yes |
| historical evaluation | Yes |
| drift monitoring | Production |
| rollback version | Production |
| deployment health endpoint | Yes |

## 18. Model Event Interface

For proactive surveillance, a model event should look conceptually like:

```json
{
  "event_id": "evt-123",
  "asset_id": "ESP-117",
  "timestamp": "...",
  "event_type": "FAILURE_RISK_INCREASE",
  "severity": "HIGH",
  "model_id": "failure-risk",
  "model_version": "2.3",
  "previous_value": 0.32,
  "current_value": 0.71,
  "drivers": ["motor_temperature_trend", "repeated_low_ROR"],
  "data_quality": "GOOD"
}
```

The Agent can then retrieve additional evidence and generate an advisory.

## 19. Mock Strategy While ML Team Is Not Ready

Build a `mock-ml-service` that implements the final contract.

Scenarios:
- NORMAL
- GAS_INTERFERENCE
- STAGE_WEAR
- INTAKE_RESTRICTION
- MOTOR_OVERHEATING
- BROKEN_SHAFT
- OVERLOAD
- SENSOR_FAILURE

Use:
- fixed fixtures
- scenario replay
- explicit `data_status = SIMULATED`

Use mocks for Agent development, tool selection, context assembly, evidence, UI and safety testing.

Do NOT use mocks to claim ML accuracy/calibration/lead time.

## 20. Recommended Development Sequence While ML Is Delayed

| Phase | Build now? | Deliverable |
|---|---:|---|
| 1 | Yes | Model contract |
| 2 | Yes | Model Adapter/Gateway |
| 3 | Yes | Mock ML Service |
| 4 | Yes | Asset Adapter |
| 5 | Yes | Telemetry Adapter |
| 6 | Yes | KB + hybrid RAG |
| 7 | Yes | Evidence Pack |
| 8 | Yes | Context Builder |
| 9 | Yes | Objectives |
| 10 | Yes | Planner/tool orchestration |
| 11 | Yes | Local Qwen runtime |
| 12 | Yes | Safety/policy gate |
| 13 | Yes | Simulator scenario benchmark |
| 14 | Later | Replace mock with real ML API |
| 15 | Later | Production model monitoring |

## 21. Minimum “ML Team Ready” Checklist

Do not integrate their production service until all are agreed:

| # | Gate |
|---:|---|
| 1 | Stable asset correlation |
| 2 | Versioned output schemas |
| 3 | Timestamp/input window |
| 4 | Data quality status |
| 5 | Confidence/probability semantics |
| 6 | Model version |
| 7 | Feature version |
| 8 | Fault/pattern taxonomy |
| 9 | Historical query |
| 10 | Failure model calibration |
| 11 | Error/timeout behavior |
| 12 | Authentication |
| 13 | Rate limits |
| 14 | Health endpoint |
| 15 | Benchmark report |
| 16 | Rollback procedure |

## 22. Most Important Contract to Freeze Now

Create an **ML → Agent Interface Agreement** with these sections:

1. Asset identification
2. Input-window semantics
3. Output schemas
4. Model versioning
5. Feature versioning
6. Confidence semantics
7. Calibration
8. Pattern/fault labels
9. Historical query behavior
10. Event/alert behavior
11. Error/unavailable behavior
12. Authentication
13. Rate/latency limits
14. Model health/version endpoint
15. Audit/provenance
16. Benchmark/release criteria

## 23. Final Architecture

```text
Advait / Simulator
      |
      +--> Asset Service
      |
      +--> Telemetry Service
      |
      +--> History/Event Service
      |
      +--> Engineering Services
      |
      +--> Digital Twin
      |
      +--> ML Model Gateway
             |
             +--> Anomaly
             +--> Failure/Degradation
             +--> Thermal/Gas/Vibration
             +--> Pattern/Fault
             +--> Health
      |
      v
Agent Tool Layer
      |
      +--> Knowledge / RAG
      +--> Evidence Pack
      +--> Context Builder
      +--> Objectives / Planner
      v
Local LLM
      |
      v
Policy/Safety Gate
      |
      v
Dashboard / Operator
```

## Final principle

**You are not blocked by the ML team being unfinished. You are blocked only if the interfaces are undefined.**

The safest parallel strategy is:

`freeze contracts → build adapters → mock services → build Agentic layer end-to-end → replace mocks with real ML services → validate against real model outputs.`

The latest guideline directly supports this architecture: ML services are independent/versioned and return structured outputs to the Agent; business logic is exposed through APIs/MCP-compatible services; the Agent integrates engineering evidence, ML, knowledge and digital-twin results rather than replacing them. 
