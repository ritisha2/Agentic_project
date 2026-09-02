"""
Canonical Telemetry Schemas for ESP Telemetry Mock API
Grounded in real MQTT broker / simulator payload — 14 VFD signal channels.

Signal namespace follows STANDARD_SENSORS in ESP_APM_models/calibration_registry.py
plus VFD STS (run-status flag). All 14 names are exactly the strings the MQTT
broker and physical VFD controller emit — no snake_case translation needed.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# ── Real 14-signal VFD canonical unit map ────────────────────────────────────
# Keys MUST match STANDARD_SENSORS in ESP_APM_models/calibration_registry.py
# plus VFD STS.  Do NOT rename — the adapter reads these keys directly.
VFD_CANONICAL_UNITS: Dict[str, str] = {
    "Inp bar/psi":        "psi",      # Intake pressure
    "Int temp °C":        "°C",       # Intake / annulus temperature
    "Motor temp °C":      "°C",       # Motor winding temperature
    "Disch pr. Bar/psi":  "psi",      # Discharge pressure
    "Vibration G's-Vx":   "g",        # Vibration X-axis (G-force)
    "Leak Current Ct":    "mA",       # Leakage current (insulation monitor)
    "Volt":               "V",        # Supply voltage
    "VSD Amps/Load":      "A",        # VSD drive current
    "Frequency":          "Hz",       # Operating frequency
    "DHG Current":        "mA",       # Downhole gauge telemetry current
    "WHP (PSI)":          "psi",      # Wellhead pressure
    "FLP (PSI)":          "psi",      # Flow line pressure
    "AP (PSI)":           "psi",      # Annulus / casing pressure
    "VFD STS":            "flag",     # VFD run-status: 1=running, 0=stopped/tripped
}


class MeasurementValue(BaseModel):
    value: float
    unit: str


class QualityMetadata(BaseModel):
    overall: str = Field(default="GOOD", description="GOOD, STALE, MISSING, INVALID, OUT_OF_RANGE, SUSPECT")
    source: str = Field(default="simulator", description="simulator, scada, mqtt, advait")
    freshness: str = Field(default="CURRENT", description="CURRENT, STALE")


class CanonicalTelemetryRecord(BaseModel):
    """
    One complete telemetry snapshot for a single ESP well.
    measurements keys use VFD names (matching VFD_CANONICAL_UNITS above).
    """
    asset_id: str
    well_id: str
    timestamp: str
    state: str = Field(default="running", description="running, stopped, tripped")
    measurements: Dict[str, MeasurementValue]   # keys are VFD signal names
    quality: QualityMetadata


class IngestTelemetryRequest(BaseModel):
    """
    Payload for POST /api/v1/telemetry (simulator / MQTT ingest endpoint).
    measurements keys can be either VFD names OR the legacy snake_case names
    (the server normalises both via VFD_CANONICAL_UNITS lookup).
    """
    asset_id: str
    timestamp: str
    state: str = Field(default="running")
    measurements: Dict[str, float]      # e.g. {"Inp bar/psi": 472.6, "Motor temp °C": 72.1, ...}
    well_id: Optional[str] = None


class TrendSeriesPoint(BaseModel):
    timestamp: str
    value: float


class TrendSeries(BaseModel):
    signal_name: str
    unit: str
    data: List[TrendSeriesPoint]
