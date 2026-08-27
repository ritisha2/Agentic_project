# Sprint 1.3 — Scope Boundary & RACI Matrix

> **Phase 1 Deliverable:** Ownership & Responsibility Freeze  
> **Grounded in:** `Guidelines.pdf` §1.3, §4.1 & `ESP_Agentic_Assistant_Architecture_Detailed_Design_UPDATED_Guideline_Mapped.docx` §3  
> **Date:** 2026-08-25  

---

## 1. Core Ownership Boundary

```text
┌─────────────────────────────────────────────────────┐
│ ESP MODEL TEAM (External)                           │
│                                                     │
│ Telemetry → Features → Rules/ML → Prediction       │
│                                                     │
│ "WHAT is happening?"                                │
└─────────────────────────┬───────────────────────────┘
                          │ REST / gRPC / Events
                          ▼
┌─────────────────────────────────────────────────────┐
│ YOUR AGENTIC TEAM (Our Scope)                       │
│                                                     │
│ KB + Tools + Objectives + Context + Evidence       │
│ + Router + LLM + Playbooks + Safety Guardrails     │
│                                                     │
│ "WHAT does it mean and WHAT should I tell/do?"     │
└─────────────────────────┬───────────────────────────┘
                          │ REST / WebSockets
                          ▼
                     OPERATOR / CLIENT
```

---

## 2. RACI Responsibility Matrix

| Subsystem Component | Agent Team | ESP ML Team | Advait Platform | Engineering Team |
|---|:---:|:---:|:---:|:---:|
| **Supervisor Agent & Router** | **R** (Responsible) | C (Consulted) | I (Informed) | C (Consulted) |
| **Objective Registry & Catalog** | **R** | C | C | C |
| **Knowledge Base & Ingestion** | **R** | C | C | **R/C** (Provides SOPs) |
| **Asset Registry & Config** | C | I | **R** (Source of Truth) | C |
| **Live Telemetry Stream** | C | C | **R** (Advait / Simulator) | I |
| **Engineering Calculations** | C | I | I | **R** (Formula Truth) |
| **4 Analytical Models** | I | **R** (Rule, Anomaly, Failure, Fault) | C | C |
| **Model Adapter & API** | C | **R** | C | I |
| **Digital Twin Simulator** | C | C | I | **R** |
| **Dashboard Agent UI** | **R/C** | C | C | C |
| **Audit & Provenance Store** | **R** | C | C | C |

---

## 3. Explicit Ownership & Source-of-Truth Decisions

```text
1. Who owns Asset Registry?
   -> Advait / Client Platform. Our system maintains a local projection cache only.

2. Who owns Tag Mapping & Canonical Units?
   -> Advait Platform defines tags. Agentic layer converts via `canonical_units.yaml`.

3. Who owns the 4 Analytical AI Models?
   -> ESP ML Team. Our Agent never retrains or executes model algorithms internally.

4. Who owns Health Index / Model Fusion?
   -> ESP ML Team. Output consumed via `get_health_index()`.

5. Who owns Engineering Calculations (TDH, ROR, BEP)?
   -> Engineering Team / Deterministic Calculation Service.

6. Who owns Pump Curves & OEM Manuals?
   -> Engineering / Knowledge Engineering. Ingested into PostgreSQL & pgvector.

7. Who owns Operational Safety Rules & Constraints?
   -> Jointly approved by Engineering & Client SOPs; enforced by Agent Guardrails.
```
