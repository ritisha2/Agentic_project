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
    VFD_CANONICAL_UNITS,          # 14-signal real VFD namespace
)

logger = logging.getLogger(__name__)

# Use the schema's authoritative VFD signal-unit map as the single source of truth
CANONICAL_UNITS = VFD_CANONICAL_UNITS

app = FastAPI(
    title="ESP Telemetry Mock API Service",
    description="MQTT/Simulator-compatible runtime telemetry service (esp-telemetry-api :8081) — 14 VFD signals",
    version="2.0.0",
)

# ---------------------------------------------------------------------------
# In-Memory Storage Engine (Current & History)
# ---------------------------------------------------------------------------
_current_snapshots: Dict[str, CanonicalTelemetryRecord] = {}
_history_records: Dict[str, List[CanonicalTelemetryRecord]] = {}
_ground_truth_scenarios: Dict[str, Dict[str, Any]] = {}


# ── Initial simulator fixtures — values from real MQTT broker / VFD controller ──

def _make_record(asset_id: str, well_id: str, measurements: Dict[str, MeasurementValue],
                 state: str = "running", scenario: str = "normal",
                 ground_truth_fault: str = "NONE") -> CanonicalTelemetryRecord:
    now_str = datetime.utcnow().isoformat() + "Z"
    record = CanonicalTelemetryRecord(
        asset_id=asset_id, well_id=well_id, timestamp=now_str,
        state=state, measurements=measurements,
        quality=QualityMetadata(overall="GOOD", source="simulator", freshness="CURRENT"),
    )
    _current_snapshots[asset_id] = record
    _history_records[asset_id] = [record]
    _ground_truth_scenarios[asset_id] = {
        "well": asset_id, "scenario": scenario, "state": state,
        "ground_truth_fault": ground_truth_fault, "is_test_fixture": True,
    }
    return record


def _populate_initial_simulator_data():
    """
    Populate baseline simulator snapshots.
    All values from real MQTT broker / VFD controller — 14 signal channels.
    Signal keys match VFD_CANONICAL_UNITS exactly (same as STANDARD_SENSORS + VFD STS).
    """

    # ── FS-031 : Normal operation baseline (Intake Gas Interference scenario) ──
    _make_record(
        asset_id="FS-031", well_id="FS-031",
        state="running", scenario="intake_gas_interference",
        ground_truth_fault="Intake Gas Interference",
        measurements={
            "Inp bar/psi":       MeasurementValue(value=236.5,  unit="psi"),
            "Int temp °C":       MeasurementValue(value=52.3,   unit="°C"),
            "Motor temp °C":     MeasurementValue(value=79.67,  unit="°C"),
            "Disch pr. Bar/psi": MeasurementValue(value=1883.7, unit="psi"),
            "Vibration G's-Vx":  MeasurementValue(value=0.1758, unit="g"),
            "Leak Current Ct":   MeasurementValue(value=15.1,   unit="mA"),
            "Volt":              MeasurementValue(value=1006.3,  unit="V"),
            "VSD Amps/Load":     MeasurementValue(value=18.86,  unit="A"),
            "Frequency":         MeasurementValue(value=46.06,  unit="Hz"),
            "DHG Current":       MeasurementValue(value=20.6,   unit="mA"),
            "WHP (PSI)":         MeasurementValue(value=48.0,   unit="psi"),
            "FLP (PSI)":         MeasurementValue(value=43.5,   unit="psi"),
            "AP (PSI)":          MeasurementValue(value=10.0,   unit="psi"),
            "VFD STS":           MeasurementValue(value=1.0,    unit="flag"),
        }
    )

    # ── FS-010 : Bearing Degradation scenario ──────────────────────────────────
    _make_record(
        asset_id="FS-010", well_id="OPG-W010",
        state="running", scenario="bearing_degradation",
        ground_truth_fault="Bearing Degradation",
        measurements={
            "Inp bar/psi":       MeasurementValue(value=1650.0, unit="psi"),
            "Int temp °C":       MeasurementValue(value=60.0,   unit="°C"),
            "Motor temp °C":     MeasurementValue(value=115.0,  unit="°C"),
            "Disch pr. Bar/psi": MeasurementValue(value=2400.0, unit="psi"),
            "Vibration G's-Vx":  MeasurementValue(value=0.48,   unit="g"),
            "Leak Current Ct":   MeasurementValue(value=18.0,   unit="mA"),
            "Volt":              MeasurementValue(value=980.0,   unit="V"),
            "VSD Amps/Load":     MeasurementValue(value=45.0,   unit="A"),
            "Frequency":         MeasurementValue(value=48.0,   unit="Hz"),
            "DHG Current":       MeasurementValue(value=21.0,   unit="mA"),
            "WHP (PSI)":         MeasurementValue(value=55.0,   unit="psi"),
            "FLP (PSI)":         MeasurementValue(value=50.0,   unit="psi"),
            "AP (PSI)":          MeasurementValue(value=12.0,   unit="psi"),
            "VFD STS":           MeasurementValue(value=1.0,    unit="flag"),
        }
    )

    # ── FS-04 : Normal Operation — simulator reference sample ─────────────────
    _make_record(
        asset_id="FS-04", well_id="FS-04",
        state="running", scenario="normal",
        ground_truth_fault="NONE",
        measurements={
            "Inp bar/psi":       MeasurementValue(value=472.6,  unit="psi"),
            "Int temp °C":       MeasurementValue(value=55.3,   unit="°C"),
            "Motor temp °C":     MeasurementValue(value=72.1,   unit="°C"),
            "Disch pr. Bar/psi": MeasurementValue(value=1957.7, unit="psi"),
            "Vibration G's-Vx":  MeasurementValue(value=0.09,   unit="g"),
            "Leak Current Ct":   MeasurementValue(value=15.1,   unit="mA"),
            "Volt":              MeasurementValue(value=294.5,   unit="V"),
            "VSD Amps/Load":     MeasurementValue(value=134.8,  unit="A"),
            "Frequency":         MeasurementValue(value=44.0,   unit="Hz"),
            "DHG Current":       MeasurementValue(value=20.6,   unit="mA"),
            "WHP (PSI)":         MeasurementValue(value=50.0,   unit="psi"),
            "FLP (PSI)":         MeasurementValue(value=45.0,   unit="psi"),
            "AP (PSI)":          MeasurementValue(value=10.0,   unit="psi"),
            "VFD STS":           MeasurementValue(value=1.0,    unit="flag"),
        }
    )

    # ── FS-OFFLINE : Sensor telemetry missing / degraded ──────────────────────
    _make_record(
        asset_id="FS-OFFLINE", well_id="Well-FS-OFFLINE",
        state="tripped", scenario="offline",
        ground_truth_fault="SENSOR_TELEMETRY_MISSING",
        measurements={
            "Inp bar/psi":       MeasurementValue(value=0.0, unit="psi"),
            "Int temp °C":       MeasurementValue(value=0.0, unit="°C"),
            "Motor temp °C":     MeasurementValue(value=0.0, unit="°C"),
            "Disch pr. Bar/psi": MeasurementValue(value=0.0, unit="psi"),
            "Vibration G's-Vx":  MeasurementValue(value=0.0, unit="g"),
            "Leak Current Ct":   MeasurementValue(value=0.0, unit="mA"),
            "Volt":              MeasurementValue(value=0.0, unit="V"),
            "VSD Amps/Load":     MeasurementValue(value=0.0, unit="A"),
            "Frequency":         MeasurementValue(value=0.0, unit="Hz"),
            "DHG Current":       MeasurementValue(value=0.0, unit="mA"),
            "WHP (PSI)":         MeasurementValue(value=0.0, unit="psi"),
            "FLP (PSI)":         MeasurementValue(value=0.0, unit="psi"),
            "AP (PSI)":          MeasurementValue(value=0.0, unit="psi"),
            "VFD STS":           MeasurementValue(value=0.0, unit="flag"),
        }
    )


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
