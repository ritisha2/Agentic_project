"""
Integration tests for Redis Streams Publisher, Consumer, and Bootstrap
Grounded in Phase 6 Event-Driven Architecture Spec §6, §8
"""

import pytest
from shared.schemas.event import ESPEvent, SeverityLevel
from src.events.redis_connection import RedisConnectionManager
from src.events.stream_bootstrap import bootstrap_streams_and_groups
from src.events.publisher import RedisStreamPublisher
from src.events.consumer import RedisStreamConsumer


def test_redis_connection_ping():
    """Verify Redis connection manager pings Redis 7 server successfully."""
    mgr = RedisConnectionManager()
    assert mgr.ping() is True


def test_stream_bootstrap_and_pubsub_roundtrip():
    """Verify bootstrap creates streams, publisher sends XADD, and consumer reads via XREADGROUP."""
    assert bootstrap_streams_and_groups() is True

    pub = RedisStreamPublisher()
    evt = ESPEvent(
        event_id="EVT-TEST-999",
        event_type="ANOMALY_DETECTED",
        asset_id="FS-031",
        source_service="anomaly-model",
        severity=SeverityLevel.MEDIUM,
        payload={"anomaly_score": 0.88, "signal_tag": "R_MOTOR_TEMP"},
        idempotency_key="IDEMP-TEST-999"
    )

    msg_id = pub.publish(evt, category="model")
    assert msg_id is not None

    consumer = RedisStreamConsumer(
        stream_name="esp:stream:model",
        group_name="esp:group:event-processor",
        consumer_name="pytest-worker"
    )

    batch = consumer.read_batch(count=5, block_ms=500)
    assert len(batch) > 0

    found = False
    for item in batch:
        if item["event"].event_id == "EVT-TEST-999":
            found = True
            consumer.ack(item["msg_id"])
            break

    assert found is True
