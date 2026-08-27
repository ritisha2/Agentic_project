# Sprint 2.3 — ESP Analytical Model Team Output API Contract

> **Phase 2 Deliverable:** Sprint 2.3 Model Output Contract Specification  
> **Source Platform:** ESP AI Model Team Runtime (Rule Engine, Anomaly, Failure/RUL, Fault Classifier)  
> **Date:** 2026-08-25  

---

## 1. Overview & Service Scope

This contract defines the standardized JSON schema that normalizes outputs from the 4 analytical AI models owned by the ESP ML Team.

```text
┌─────────────────────────────────────────────────────┐
│ ESP MODEL TEAM RUNTIME                              │
│                                                     │
│ ├── Model 1: Rule Engine                            │
│ ├── Model 2: Anomaly Detection                      │
│ ├── Model 3: Failure Prediction & RUL               │
│ └── Model 4: Fault Classifier                       │
└─────────────────────────┬───────────────────────────┘
                          │ REST / gRPC / Events
                          ▼
┌─────────────────────────────────────────────────────┐
│ MODEL ADAPTER (`src/adapters/model_adapter.py`)     │
│ Normalizes into ModelOutputPayload                 │
└─────────────────────────────────────────────────────┘
```

---

## 2. API Endpoints

### 2.1 Get Consolidated Model Output
- **Endpoint:** `GET /api/v1/assets/{asset_id}/model-output`
- **Response `200 OK`:**
```json
{
  "asset_id": "ESP-Well-001",
  "timestamp": "2026-08-25T12:00:00Z",
  "rules": {
    "violations": ["MOTOR_TEMP_MARGIN_LOW"],
    "deviation_counts": {
      "1h": 2,
      "24h": 5,
      "30d": 12
    }
  },
  "anomaly": {
    "anomaly_score": 0.91,
    "status": "ANOMALOUS",
    "contributing_signals": ["motor_temperature", "winding_temp"]
  },
  "failure": {
    "risk_24h": 0.72,
    "risk_72h": 0.88,
    "risk_7d": 0.95,
    "rul_hours": 75.0,
    "primary_failure_mode": "MOTOR_BURNOUT"
  },
  "fault": {
    "predicted_fault_class": "MOTOR_OVERHEATING",
    "confidence": 0.87,
    "supporting_evidence_features": ["motor_temperature = 135°C", "current = 62A"]
  },
  "health": {
    "health_index": 45,
    "status": "CRITICAL",
    "contributors": ["Thermal Overload", "High 24h Risk"]
  },
  "model_versions": {
    "rule_engine": "1.2.0",
    "anomaly_detector": "2.1.0",
    "failure_predictor": "1.5.0",
    "fault_classifier": "3.0.1"
  }
}
```

---

## 3. Strict Contract Verification Rule

- **Fault Taxonomy Consistency:** `set(kb_faults) == set(model_faults)`  
  Every predicted fault class returned by the Model Team's Fault Classifier MUST match a valid `fault_code` registered in `esp-knowledge/deterministic/faults/seed_faults.yaml` and the PostgreSQL `fault_patterns` table.
