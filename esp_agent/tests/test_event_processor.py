"""
Unit tests for EventProcessor & EventReplayEngine
Grounded in Phase 6 Event-Driven Architecture Spec §10, §15, §29
"""

import uuid
import pytest
from shared.schemas.event import ESPEvent, SeverityLevel
from src.events.processor import EventProcessor
from src.events.replay_engine import EventReplayEngine
from src.events.db_event_store import DatabaseEventStore


def test_event_processor_deduplication(tmp_path):
    """Verify EventProcessor drops duplicate idempotency keys."""
    db_file = str(tmp_path / "proc_test.db")
    db_store = DatabaseEventStore(db_path=db_file)
    processor = EventProcessor(db_store=db_store)
    uid = uuid.uuid4().hex[:8]

    evt1 = ESPEvent(
        event_id=f"EVT-PROC-{uid}",
        event_type="ESP_TRIPPED",
        asset_id="FS-031",
        source_service="scada",
        severity=SeverityLevel.CRITICAL,
        idempotency_key=f"UNIQUE-KEY-{uid}"
    )

    # First attempt: should succeed & promote to actionable
    is_act1, reason1 = processor.process_event(evt1)
    assert is_act1 is True
    assert reason1 == "ACTIONABLE_PROMOTED"

    # Second attempt with same idempotency key: should be detected as duplicate
    is_act2, reason2 = processor.process_event(evt1)
    assert is_act2 is False
    assert reason2 == "DUPLICATE_SKIPPED"


def test_event_processor_hysteresis(tmp_path):
    """Verify EventProcessor enforces hysteresis min_persistence_samples for FAILURE_RISK_INCREASED."""
    db_file = str(tmp_path / "hys_test.db")
    db_store = DatabaseEventStore(db_path=db_file)
    processor = EventProcessor(db_store=db_store)
    uid = uuid.uuid4().hex[:8]
    asset_id = f"FS-{uid}"

    # FAILURE_RISK_INCREASED requires 3 samples in 900s window
    evt_a = ESPEvent(
        event_id=f"EVT-RISK-101-{uid}",
        event_type="FAILURE_RISK_INCREASED",
        asset_id=asset_id,
        source_service="ml-model",
        severity=SeverityLevel.HIGH,
        idempotency_key=f"RISK-KEY-101-{uid}"
    )
    is_act_a, reason_a = processor.process_event(evt_a)
    assert is_act_a is False
    assert reason_a == "HYSTERESIS_UNSATISFIED"

    evt_b = ESPEvent(
        event_id=f"EVT-RISK-102-{uid}",
        event_type="FAILURE_RISK_INCREASED",
        asset_id=asset_id,
        source_service="ml-model",
        severity=SeverityLevel.HIGH,
        idempotency_key=f"RISK-KEY-102-{uid}"
    )
    is_act_b, reason_b = processor.process_event(evt_b)
    assert is_act_b is False

    evt_c = ESPEvent(
        event_id=f"EVT-RISK-103-{uid}",
        event_type="FAILURE_RISK_INCREASED",
        asset_id=asset_id,
        source_service="ml-model",
        severity=SeverityLevel.HIGH,
        idempotency_key=f"RISK-KEY-103-{uid}"
    )
    is_act_c, reason_c = processor.process_event(evt_c)
    assert is_act_c is True
    assert reason_c == "ACTIONABLE_PROMOTED"


def test_event_replay_engine(tmp_path):
    """Verify EventReplayEngine reads history from DB store."""
    db_file = str(tmp_path / "replay_test.db")
    db_store = DatabaseEventStore(db_path=db_file)
    processor = EventProcessor(db_store=db_store)
    replay = EventReplayEngine(db_store=db_store, processor=processor)

    evt = ESPEvent(
        event_id="EVT-REPLAY-1",
        event_type="ESP_TRIPPED",
        asset_id="FS-031",
        source_service="scada",
        severity=SeverityLevel.CRITICAL,
        idempotency_key="REPLAY-KEY-1"
    )
    db_store.save_event(evt)

    res = replay.replay_asset_history("FS-031", limit=10, dry_run=True)
    assert res["replayed_count"] == 1
    assert res["asset_id"] == "FS-031"
