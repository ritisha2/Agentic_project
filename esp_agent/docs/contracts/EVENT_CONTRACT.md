# Sprint 2.4 — Event & Alert Service Contract

> **Phase 2 Deliverable:** Sprint 2.4 Event & Alert Contract Specification  
> **Source Platform:** Event Bus (Kafka / RabbitMQ / Redis Streams / WebSockets)  
> **Date:** 2026-08-25  

---

## 1. Overview & Service Scope

The **Event Service** consumes real-time model events and alert triggers pushed by the Model Runtime, enabling the Agent to execute proactive surveillance.

---

## 2. Event Payload Schema

```json
{
  "event_id": "EVT-98412",
  "event_type": "RISK_ELEVATED",
  "asset_id": "ESP-Well-001",
  "timestamp": "2026-08-25T12:00:00Z",
  "severity": "CRITICAL",
  "source_model": "FailurePredictor_v1.5",
  "summary": "24h failure risk increased from 0.32 to 0.72",
  "trigger_metrics": {
    "motor_temperature": 135.0,
    "risk_24h": 0.72
  },
  "suggested_objective": "OBJ_EXPLAIN_ALERT"
}
```

---

## 3. Event Processing Rules

1. **Idempotency:** Duplicate events within a 300-second window are suppressed based on `event_id` and `asset_id`.
2. **Proactive Trigger:** When a `CRITICAL` or `HIGH` event arrives, the Agent automatically triggers `ObjectiveRouter.route_and_execute(suggested_objective, asset_id)` to prepare an advisory for the operator dashboard.
