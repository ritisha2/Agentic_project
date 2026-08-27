"""
Canonical Telemetry Schemas for ESP Telemetry Mock API
Grounded in ESP_APM_Telemetry_Mock_API_Specification.docx §§5–9
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class MeasurementValue(BaseModel):
    value: float
    unit: str


class QualityMetadata(BaseModel):
    overall: str = Field(default="GOOD", description="GOOD, STALE, MISSING, INVALID, OUT_OF_RANGE, SUSPECT")
    source: str = Field(default="simulator", description="simulator, scada, advait")
    freshness: str = Field(default="CURRENT", description="CURRENT, STALE")


class CanonicalTelemetryRecord(BaseModel):
    asset_id: str
    well_id: str
    timestamp: str
    state: str = Field(default="running", description="running, stopped, tripped")
    measurements: Dict[str, MeasurementValue]
    quality: QualityMetadata


class IngestTelemetryRequest(BaseModel):
    asset_id: str
    timestamp: str
    state: str = Field(default="running")
    measurements: Dict[str, float]  # e.g. {"liquid_rate": 735.7, "intake_pressure": 236.5, ...}
    well_id: Optional[str] = None


class TrendSeriesPoint(BaseModel):
    timestamp: str
    value: float


class TrendSeries(BaseModel):
    signal_name: str
    unit: str
    data: List[TrendSeriesPoint]
