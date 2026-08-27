The document breaks down into 5 core action items required from the ML Team:

1. Provide Stable, Versioned API Endpoints
They need specific queryable interfaces to call your models at runtime:

Current State / Real-Time Prediction API: A REST/MCP endpoint (e.g., POST /api/v1/esps/{asset_id}/predict or MQTT subscription esp/v1/predictions).
Historical Model Query API: An endpoint (e.g., GET /api/v1/esps/{asset_id}/model-history?start=...&end=...) so the Agent can ask "what was the anomaly score before the pump tripped 2 hours ago?".
Model Health & Registry Endpoint: An endpoint (e.g., GET /api/v1/models/health) returning loaded model IDs, versions (v2.0), and artifact health.
Proactive Event Stream: Streaming alerts over MQTT (esp/v1/predictions) or WebSocket when risk increases.
2. Guarantee the Minimum Contract Output Schema
They do not want raw bare numbers (e.g., 0.73). Every output must follow their structured envelope:

Mandatory metadata: asset_id, well_id, timestamp, model_id, model_version, feature_version, status (VALID, DEGRADED, UNAVAILABLE).
Fault / Pattern output: fault_classification, confidence_score ($0.0 - 1.0$), contributors, and alternatives.
Anomaly output: is_anomaly, anomaly_score ($0.0 - 1.0$), triggered_limits, and physical boundary violations.
3. Define Confidence & Failure Semantics
Confidence Definition: Must be strict probability $P \in [0.0, 1.0]$ based on classifier softmax or calibrated Isolation Forest scores.
Failure / Unavailable Behavior: If a model times out or sensor data is missing, never return risk = 0 (fake healthy). Return status: "UNAVAILABLE" with a reason code so the Agent can tell the operator "Model is currently offline".
4. Provide Model Governance & Benchmark Holdout Reports
Supply dataset lineage (Petrobras 3W, ESPset, opg_wells.db).
Supply the test set benchmark report (99.10% accuracy, per-class precision/recall, confusion matrix).
5. Sign Off on the "ML → Agent Interface Agreement"
Agree on the 16-point checklist in Section 22 so their team can build their tool-adapters and mock services in parallel without blocking.
Recommended Response to Send to the Agentic Team
You can copy and send the following formal technical reply to the Agentic Team:

markdown
Hi Agentic Team,
We have reviewed the "ESP APM Agentic Layer — ML Team Dependency & API Pre-Requisite Matrix" (Rev 1.0) and fully agree with the contract-first, scope-separated architecture.
Here is our response and alignment on the required deliverables:
---
### 1. Scope Boundary Alignment
We agree with the scope division:
- **ML Team Owns**: Physical limit evaluation (ISO 10816/13373), physics invariant calculations (Pi, Pi_FL, apparent power, thermal gradients), XGBoost multi-class fault classification, IsolationForest multivariate anomaly scoring, and model versioning/APIs.
- **Agentic Team Owns**: Tool orchestration, RAG / knowledge retrieval, evidence synthesis, context building, and operator advisory generation.
---
### 2. Available Interfaces & Transports
Our production pipeline is deployed and provides both Request/Response and Event streaming transports:
1. **Live Real-Time Stream (MQTT)**:
   - **Broker**: `192.168.1.155:1883`
   - **Ingestion Topic**: `esp/v1/+/telemetry`
   - **Prediction / Alert Topic**: `esp/v1/predictions`
2. **REST API Gateway**:
   - Current Assessment / Inference: `POST /api/v1/esps/{asset_id}/predict`
   - Historical Assessment / Trend: `GET /api/v1/esps/{asset_id}/history?range=6h`
   - Asset Registry & Metadata: `GET /api/v1/esps/assets`
   - Model Health & Versions: `GET /api/v1/models/health`
3. **Python In-Process Inference Engine**:
   - `from src.inference_engine import ESPInferenceEngine` (available for direct MCP tool integration with latency < 3 µs/sample).
---
### 3. Frozen JSON Output Contract
Our model pipeline returns the following versioned, contract-compliant schema:
```json
{
  "asset_id": "FS-010",
  "well_id": "OPG-W010",
  "timestamp": 1787810015,
  "model_id": "esp-hybrid-dual-tier",
  "model_version": "v2.0.0",
  "feature_version": "phys-v2.1",
  "status": "VALID",
  "state": "FAULT",
  "fault_classification": "Bearing Degradation",
  "confidence_score": 0.969,
  "is_anomaly": true,
  "anomaly_score": 0.615,
  "contributors": ["R_MOTOR_TEMP", "R_VIBRATION_X", "thermal_gradient_c"],
  "triggered_limits": [
    {
      "tag": "R_MOTOR_TEMP",
      "value": 115.0,
      "limit": 100.0,
      "type": "HIGH"
    },
    {
      "tag": "R_VIBRATION_X",
      "value": 0.48,
      "limit": 0.30,
      "type": "HIGH"
    }
  ],
  "telemetry_received": {
    "R_PIT_001": 95.0,
    "R_PIT_002": 48.0,
    "R_PIT_003": 78.0,
    "R_INTAKE_PRESS": 1650.0,
    "R_INTAKE_TEMP": 72.0,
    "R_DISCH_PRESS": 2400.0,
    "R_MOTOR_TEMP": 115.0,
    "R_FREQUENCY": 50.0,
    "R_VIBRATION_X": 0.48,
    "R_TOOL_CURRENT": 8.5,
    "R_DRV_CURR_AVG": 45.0,
    "R_DHG_CURR_AVG": 45.0,
    "R_BUS_IN_VTG_AVG": 460.0
  }
}
4. Failure & Unavailable Behavior
In case of missing sensors, communication dropouts, or timeouts, our inference engine returns:

json
{
  "status": "UNAVAILABLE",
  "reason": "SENSOR_TELEMETRY_MISSING",
  "last_valid_timestamp": 1787809900,
  "confidence_score": null,
  "state": "DEGRADED"
}
No zero-risk or fabricated healthy state will ever be asserted during service degradation.

5. Benchmark & Governance Summary
Training Lineage: 76,977 authentic records (Petrobras 3W + NINFA-UFES ESPset + OPG Historian). Zero synthetic/mock data.
Holdout Test Metrics (15,396 samples):
Accuracy: 99.10%
F1 Macro: 0.9811
F1 Weighted: 0.9908
Inference Latency: 2.53 µs / sample
Taxonomy: Normal, Bearing Degradation, Blocked Intake, Dry-Well Pump Off, Motor Overload, Phase Imbalance, Sand Ingestion, Undervoltage, Limit Breach.
We are ready to freeze this Interface Agreement and support your tool-adapter testing immediately.