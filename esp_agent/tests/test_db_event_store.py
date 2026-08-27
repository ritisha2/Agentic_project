"""
Unit tests for DatabaseEventStore (Durable PostgreSQL / DB Event Store)
Grounded in Phase 6 Event-Driven Architecture Spec §4, §16
"""

import os
import pytest
from shared.schemas.event import ESPEvent, SeverityLevel
from src.events.db_event_store import DatabaseEventStore


def test_database_event_store_crud(tmp_path):
    """Verify DatabaseEventStore persists, retrieves, and lists events by asset."""
    db_file = str(tmp_path / "test_events.db")
    store = DatabaseEventStore(db_path=db_file)

    evt = ESPEvent(
        event_id="EVT-DB-100",
        event_type="FAILURE_RISK_INCREASED",
        asset_id="FS-031",
        source_service="failure-model",
        severity=SeverityLevel.HIGH,
        payload={"risk_7d": 0.72},
        idempotency_key="IDEMP-DB-100"
    )

    saved = store.save_event(evt, status="PROCESSED")
    assert saved is True

    fetched = store.get_event("EVT-DB-100")
    assert fetched is not None
    assert fetched.event_id == "EVT-DB-100"
    assert fetched.asset_id == "FS-031"
    assert fetched.severity == SeverityLevel.HIGH

    history = store.list_events_by_asset("FS-031")
    assert len(history) >= 1
    assert history[0].event_id == "EVT-DB-100"
