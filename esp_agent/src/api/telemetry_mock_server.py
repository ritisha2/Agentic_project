"""
ESP Telemetry Mock API Server (esp-telemetry-api :8081)
Grounded in ESP_APM_Telemetry_Mock_API_Specification.docx §§1–21

Standalone FastAPI service providing simulator ingestion, canonical normalization,
current snapshot storage, history time-series queries, and QoD audit endpoints.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query, Response, status
import uvicorn

from src.api.telemetry_mock_schemas import (
    CanonicalTelemetryRecord,
    IngestTelemetryRequest,
    MeasurementValue,
    QualityMetadata,
    TrendSeries,
    TrendSeriesPoint,
)

logger = logging.getLogger(__name__)

# Canonical Signal Unit Mapping (§6)
CANONICAL_UNITS = {
    "liquid_rate": "BPD",
    "intake_pressure": "psi",
    "discharge_pressure": "psi",
    "frequency": "Hz",
    "motor_current": "A",
    "motor_voltage": "V",
    "motor_temperature": "degC",
    "vibration_rms": "g",
    "voltage_imbalance": "%",
    "current_imbalance": "%",
}

app = FastAPI(
    title="ESP Telemetry Mock API Service",
    description="Simulator-compatible runtime telemetry service (esp-telemetry-api :8081)",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# In-Memory Storage Engine (Current & History)
# ---------------------------------------------------------------------------
_current_snapshots: Dict[str, CanonicalTelemetryRecord] = {}
_history_records: Dict[str, List[CanonicalTelemetryRecord]] = {}
_ground_truth_scenarios: Dict[str, Dict[str, Any]] = {}


def _populate_initial_simulator_data():
    """Populate baseline FS-031 simulator sample (§2)."""
    now_str = datetime.utcnow().isoformat() + "Z"
    record = CanonicalTelemetryRecord(
        asset_id="FS-031",
        well_id="FS-031",
        timestamp=now_str,
        state="running",
        measurements={
            "liquid_rate": MeasurementValue(value=735.7, unit="BPD"),
            "intake_pressure": MeasurementValue(value=236.5, unit="psi"),
            "discharge_pressure": MeasurementValue(value=1883.7, unit="psi"),
            "frequency": MeasurementValue(value=46.06, unit="Hz"),
            "motor_current": MeasurementValue(value=18.86, unit="A"),
            "motor_voltage": MeasurementValue(value=1006.3, unit="V"),
            "motor_temperature": MeasurementValue(value=79.67, unit="degC"),
            "vibration_rms": MeasurementValue(value=0.1758, unit="g"),
            "voltage_imbalance": MeasurementValue(value=0.60, unit="%"),
            "current_imbalance": MeasurementValue(value=1.00, unit="%"),
        },
        quality=QualityMetadata(overall="GOOD", source="simulator", freshness="CURRENT"),
    )
    _current_snapshots["FS-031"] = record
    _history_records["FS-031"] = [record]
    _ground_truth_scenarios["FS-031"] = {
        "well": "FS-031",
        "scenario": "normal",
        "state": "running",
        "ground_truth_fault": "NONE",
        "is_test_fixture": True,
    }


_populate_initial_simulator_data()


# ---------------------------------------------------------------------------
# Health & Service Operations (§8)
# ---------------------------------------------------------------------------
@app.get("/health", tags=["system"])
def health():
    return {"status": "UP", "timestamp": datetime.utcnow().isoformat() + "Z"}


@app.get("/readiness", tags=["system"])
def readiness():
    return {"status": "READY", "store": "in-memory", "assets_loaded": len(_current_snapshots)}


@app.get("/version", tags=["system"])
def version():
    return {
        "service": "esp-telemetry-api",
        "version": "1.0.0",
        "schema_version": "1.0",
        "spec_reference": "ESP_APM_Telemetry_Mock_API_Specification.docx",
    }


# ---------------------------------------------------------------------------
# Telemetry Ingestion API (§9)
# ---------------------------------------------------------------------------
@app.post("/api/v1/telemetry", status_code=status.HTTP_201_CREATED, tags=["ingestion"])
def ingest_telemetry(payload: IngestTelemetryRequest):
    """
    Ingest runtime simulator telemetry sample (§9).
    Normalizes measurement dict to canonical signals & units.
    """
    if not payload.asset_id or not payload.timestamp:
        raise HTTPException(status_code=422, detail="INVALID_TELEMETRY: asset_id and timestamp are required.")

    well_id = payload.well_id or payload.asset_id
    canonical_measurements: Dict[str, MeasurementValue] = {}

    for name, val in payload.measurements.items():
        unit = CANONICAL_UNITS.get(name, "raw")
        canonical_measurements[name] = MeasurementValue(value=float(val), unit=unit)

    record = CanonicalTelemetryRecord(
        asset_id=payload.asset_id,
        well_id=well_id,
        timestamp=payload.timestamp,
        state=payload.state,
        measurements=canonical_measurements,
        quality=QualityMetadata(overall="GOOD", source="simulator", freshness="CURRENT"),
    )

    # Update current snapshot & append history
    _current_snapshots[payload.asset_id] = record
    if payload.asset_id not in _history_records:
        _history_records[payload.asset_id] = []
    _history_records[payload.asset_id].append(record)

    logger.info(f"Ingested telemetry sample for {payload.asset_id} at {payload.timestamp}")
    return {
        "status": "SUCCESS",
        "asset_id": payload.asset_id,
        "well_id": well_id,
        "timestamp": payload.timestamp,
        "signals_ingested": len(canonical_measurements),
    }


# ---------------------------------------------------------------------------
# Telemetry Read APIs (§10–13)
# ---------------------------------------------------------------------------
@app.get("/api/v1/assets", tags=["read"])
def list_assets():
    """List known telemetry assets."""
    return {"assets": list(_current_snapshots.keys())}


@app.get("/api/v1/assets/{asset_id}/telemetry/current", tags=["read"])
def get_current_telemetry(asset_id: str):
    """Fetch latest canonical telemetry record for specified asset (§10)."""
    if asset_id not in _current_snapshots:
        raise HTTPException(status_code=404, detail=f"NOT_FOUND: Unknown asset '{asset_id}'.")
    return _current_snapshots[asset_id]


@app.get("/api/v1/assets/{asset_id}/telemetry/history", tags=["read"])
def get_historical_telemetry(
    asset_id: str,
    from_time: Optional[str] = Query(None, alias="from"),
    to_time: Optional[str] = Query(None, alias="to"),
    interval: Optional[str] = Query("1m"),
    signals: Optional[str] = Query(None),
):
    """Fetch historical telemetry time window (§11)."""
    if asset_id not in _history_records:
        raise HTTPException(status_code=404, detail=f"NOT_FOUND: Unknown asset '{asset_id}'.")

    records = _history_records[asset_id]
    signal_list = [s.strip() for s in signals.split(",")] if signals else None

    filtered_records = []
    for r in records:
        if signal_list:
            filtered_meas = {k: v for k, v in r.measurements.items() if k in signal_list}
        else:
            filtered_meas = r.measurements

        filtered_records.append({
            "timestamp": r.timestamp,
            "state": r.state,
            "measurements": {k: v.model_dump() for k, v in filtered_meas.items()},
        })

    return {
        "asset_id": asset_id,
        "well_id": _current_snapshots[asset_id].well_id,
        "count": len(filtered_records),
        "history": filtered_records,
    }


@app.get("/api/v1/assets/{asset_id}/telemetry/trend", tags=["read"])
def get_telemetry_trend(
    asset_id: str,
    signals: str = Query("liquid_rate,intake_pressure,discharge_pressure"),
):
    """Fetch trend-ready multi-signal series format for UI charts."""
    if asset_id not in _history_records:
        raise HTTPException(status_code=404, detail=f"NOT_FOUND: Unknown asset '{asset_id}'.")

    target_signals = [s.strip() for s in signals.split(",")]
    records = _history_records[asset_id]
    trends: Dict[str, TrendSeries] = {}

    for sig in target_signals:
        unit = CANONICAL_UNITS.get(sig, "raw")
        points = []
        for r in records:
            if sig in r.measurements:
                points.append(TrendSeriesPoint(timestamp=r.timestamp, value=r.measurements[sig].value))
        trends[sig] = TrendSeries(signal_name=sig, unit=unit, data=points)

    return {
        "asset_id": asset_id,
        "trends": {k: v.model_dump() for k, v in trends.items()},
    }


@app.get("/api/v1/assets/{asset_id}/telemetry/quality", tags=["read"])
def get_telemetry_quality(asset_id: str):
    """Fetch QoD/freshness audit report (§12)."""
    if asset_id not in _current_snapshots:
        raise HTTPException(status_code=404, detail=f"NOT_FOUND: Unknown asset '{asset_id}'.")

    record = _current_snapshots[asset_id]
    return {
        "asset_id": asset_id,
        "well_id": record.well_id,
        "quality": record.quality.model_dump(),
        "timestamp": record.timestamp,
        "signal_count": len(record.measurements),
    }


@app.get("/api/v1/assets/{asset_id}/telemetry/schema", tags=["read"])
def get_telemetry_schema(asset_id: str):
    """Fetch signal schema definitions & units (§6)."""
    return {
        "asset_id": asset_id,
        "canonical_signals": CANONICAL_UNITS,
    }


# ---------------------------------------------------------------------------
# Test-Only Ground-Truth Endpoint (§18)
# ---------------------------------------------------------------------------
@app.get("/api/v1/test/assets/{asset_id}/ground-truth", tags=["test_only"])
def get_ground_truth_test_scenario(asset_id: str):
    """
    TEST ONLY: Ground truth simulation scenario details (§18).
    Isolated from production Agent tools.
    """
    if asset_id not in _ground_truth_scenarios:
        raise HTTPException(status_code=404, detail=f"NOT_FOUND: Ground truth scenario unavailable for '{asset_id}'.")
    return _ground_truth_scenarios[asset_id]


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
