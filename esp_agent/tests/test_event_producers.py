"""
Unit tests for ModelEventProducer and TelemetryEventDetector
Grounded in Phase 6 Event-Driven Architecture Spec §7, §18
"""

import pytest
from src.events.producers.model_producer import ModelEventProducer
from src.events.producers.telemetry_detector import TelemetryEventDetector


def test_model_event_producer_publish():
    """Verify ModelEventProducer publishes FAILURE_RISK_INCREASED event."""
    producer = ModelEventProducer()
    msg_id = producer.emit_failure_risk_increased(
        asset_id="FS-031",
        risk_7d=0.74,
        previous_risk_7d=0.41,
        correlation_id="CORR-TEST-MODEL-1"
    )
    assert msg_id is not None


def test_telemetry_event_detector_threshold():
    """Verify TelemetryEventDetector detects production drop and emits event."""
    detector = TelemetryEventDetector()
    msg_id = detector.evaluate_telemetry("FS-031", {"flow_rate": 1100.0, "motor_temperature": 90.0})
    assert msg_id is not None
