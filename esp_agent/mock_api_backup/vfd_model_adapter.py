"""
VFD Model Adapter (v2)
======================
Bridges esp_agent Telemetry Mock API (:8081) -> ESP_APM_models.WellDiagnosticEngine.

v2 change: TEL API now uses the REAL 14 VFD signal names directly (matching
STANDARD_SENSORS in calibration_registry.py + VFD STS). The adapter is now
largely a passthrough with unit-value extraction and a VFD STS state check.
"""

import os
import sys
import logging
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# -- Make ESP_APM_models importable from esp_agent process --------------------
_PACKAGE_DIR  = os.path.dirname(os.path.abspath(__file__))
_AGENTIC_ROOT = os.path.normpath(os.path.join(_PACKAGE_DIR, "..", "..", "..", ".."))

if _AGENTIC_ROOT not in sys.path:
    sys.path.insert(0, _AGENTIC_ROOT)

try:
    from ESP_APM_models.diagnostic_engine import WellDiagnosticEngine
    from ESP_APM_models.calibration_registry import STANDARD_SENSORS
    _ENGINE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"[vfd_model_adapter] ESP_APM_models not importable: {e}. Adapter will return mock output.")
    _ENGINE_AVAILABLE = False
    STANDARD_SENSORS = []


# -- VFD signal namespace (matches TEL API VFD_CANONICAL_UNITS + STANDARD_SENSORS) --
# TEL API now serves all 14 with these exact keys — no rename needed.
# VFD STS is state metadata, not a sensor fed into the engine.
_VFD_SIGNAL_DEFAULTS: Dict[str, float] = {
    "Inp bar/psi":       300.0,
    "Int temp \u00b0C":      55.0,
    "Motor temp \u00b0C":    75.0,
    "Disch pr. Bar/psi": 1500.0,
    "Vibration G's-Vx":  0.15,
    "Leak Current Ct":   15.0,
    "Volt":              400.0,
    "VSD Amps/Load":     30.0,
    "Frequency":         50.0,
    "DHG Current":       20.0,
    "WHP (PSI)":         50.0,
    "FLP (PSI)":         45.0,
    "AP (PSI)":          10.0,
}


# -- Pydantic output contract --------------------------------------------------

class VFDDynamics(BaseModel):
    delta_p: float = Field(description="Differential head pressure dP = Disch - Intake (PSI)")
    torque_proxy: float = Field(description="Torque proxy t = Amps / Hz  (A/Hz)")
    power_proxy_kva: float = Field(description="Apparent power sqrt(3) x V x I / 1000  (kVA)")
    thermal_elevation: float = Field(description="Thermal elevation dT = Motor_C - Intake_C")
    thermal_rate_hr: float = Field(default=0.0, description="Thermal rate of change dT/dt (deg C/hr)")
    pressure_ratio: float = Field(description="Pressure ratio Disch / Intake")


class VFDRootCauseDriver(BaseModel):
    sensor: str
    observation: str


class VFDDiagnosticResult(BaseModel):
    """
    Structured output of the VFD Model Adapter.
    Consumed by LangGraph model_specialist node and mapped into
    AdvisoryEvidenceItem (EVID-ML-VFD-{fault_slug}) entries.
    """
    asset_id: str
    well_id: str
    family: str = Field(default="UNKNOWN")
    timestamp: str
    vfd_sts: int = Field(default=1, description="VFD run status flag: 1=running, 0=stopped/tripped")

    # Core diagnostic
    health_score: float = Field(description="Composite Health Index 0-100")
    status: str = Field(description="NORMAL | CAUTION | CRITICAL | TRIPPED")
    primary_fault: str = Field(description="Primary fault classification from 13-mode matrix")
    confidence: str = Field(description="Confidence string, e.g. 88.0%")
    est_time_to_trip: str = Field(description="Estimated operational runway to trip")
    description: str = Field(description="Plain-language fault description")
    action_advisory: str = Field(description="Recommended operator action")

    # Root causes and dynamics
    root_cause_drivers: List[VFDRootCauseDriver] = Field(default_factory=list)
    dynamics: VFDDynamics

    # ML anomaly
    is_anomaly: bool = Field(default=False)
    anomaly_score: float = Field(default=0.0, description="IsolationForest anomaly score 0.0-1.0")

    # Normalized feature vector (for downstream ML / evidence)
    normalized_features: Dict[str, float] = Field(default_factory=dict)

    # Source tracing
    signals_mapped: int = Field(description="TEL API signals successfully mapped")
    signals_filled: List[str] = Field(default_factory=list, description="Signals filled from calibrated defaults")
    engine_available: bool = Field(description="True = live engine; False = fallback mock")


# -- Singleton engine (loaded once at startup) ---------------------------------
_engine: Optional["WellDiagnosticEngine"] = None


def _get_engine() -> Optional["WellDiagnosticEngine"]:
    global _engine
    if not _ENGINE_AVAILABLE:
        return None
    if _engine is None:
        try:
            _engine = WellDiagnosticEngine()
            logger.info("[vfd_model_adapter] WellDiagnosticEngine loaded successfully.")
        except Exception as e:
            logger.error(f"[vfd_model_adapter] Failed to initialise WellDiagnosticEngine: {e}")
    return _engine


# -- Signal extraction ---------------------------------------------------------

def _extract_vfd_signals(
    measurements: Dict[str, Any]
) -> Tuple[Dict[str, float], int, List[str]]:
    """
    Extracts the 13 engine signals + VFD STS from a CanonicalTelemetryRecord.measurements dict.
    Since TEL API v2 uses VFD names directly, this is now a near-passthrough:
    just unwrap {"value": float, "unit": str} dicts and fill any missing signals from defaults.

    Returns:
        raw_vfd   - 13-channel dict for WellDiagnosticEngine
        vfd_sts   - VFD run status (1=running, 0=stopped/tripped)
        filled    - List of signal names filled from defaults
    """
    raw_vfd: Dict[str, float] = {}
    filled: List[str] = []

    def _to_float(v: Any) -> float:
        if isinstance(v, dict):
            return float(v.get("value", 0.0))
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    # Extract all 14 signals (VFD names are already correct)
    for sig in STANDARD_SENSORS + ["VFD STS"]:
        if sig in measurements:
            raw_vfd[sig] = _to_float(measurements[sig])
        else:
            filled.append(sig)
            raw_vfd[sig] = _VFD_SIGNAL_DEFAULTS.get(sig, 0.0)

    # Pull VFD STS out of engine input (it is not a STANDARD_SENSORS channel)
    vfd_sts = int(raw_vfd.pop("VFD STS", 1))
    if "VFD STS" in filled:
        filled.remove("VFD STS")

    return raw_vfd, vfd_sts, filled


# -- Public API ----------------------------------------------------------------

def run_vfd_diagnostic(
    asset_id: str,
    measurements: Dict[str, Any],
    prev_measurements: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None,
) -> VFDDiagnosticResult:
    """
    Main entry point for the VFD Model Adapter.

    Args:
        asset_id:          Well ID e.g. "FS-031"
        measurements:      measurements dict from CanonicalTelemetryRecord
                           (TEL API v2: keys are VFD names, values are {"value": float, "unit": str})
        prev_measurements: Previous-step measurements for dT/dt gradient (optional)
        timestamp:         ISO timestamp string (optional)

    Returns:
        VFDDiagnosticResult ready for LangGraph model_specialist consumption
    """
    import datetime as _dt

    ts = timestamp or _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    raw_vfd, vfd_sts, filled = _extract_vfd_signals(measurements)
    prev_vfd, _, _ = _extract_vfd_signals(prev_measurements) if prev_measurements else ({}, 1, [])

    engine = _get_engine()

    if engine is None:
        logger.warning("[vfd_model_adapter] Returning mock diagnostic result (engine unavailable).")
        return VFDDiagnosticResult(
            asset_id=asset_id, well_id=asset_id, family="UNKNOWN", timestamp=ts,
            vfd_sts=vfd_sts,
            health_score=75.0, status="CAUTION", primary_fault="Model Unavailable",
            confidence="N/A", est_time_to_trip="Unknown",
            description="ESP_APM_models engine could not be loaded. Verify package path and dependencies.",
            action_advisory="Check agent gateway logs for import errors.",
            root_cause_drivers=[],
            dynamics=VFDDynamics(
                delta_p=0.0, torque_proxy=0.0, power_proxy_kva=0.0,
                thermal_elevation=0.0, thermal_rate_hr=0.0, pressure_ratio=0.0
            ),
            is_anomaly=False, anomaly_score=0.0, normalized_features={},
            signals_mapped=len(measurements) - len(filled),
            signals_filled=filled, engine_available=False,
        )

    try:
        result = engine.evaluate_live_telemetry(
            well_id=asset_id,
            raw_telemetry=raw_vfd,
            prev_telemetry=prev_vfd or None,
            verbose=False,
        )
    except Exception as e:
        logger.error(f"[vfd_model_adapter] Engine evaluation failed for {asset_id}: {e}")
        raise

    diag = result["diagnostic"]
    dyn  = result["dynamics"]
    ml   = result["ml_anomaly"]

    root_cause_drivers = [
        VFDRootCauseDriver(sensor=s, observation=o)
        for s, o in diag.get("root_cause_drivers", [])
    ]

    status_clean = str(diag.get("status", "UNKNOWN"))
    for emoji in ["\U0001f7e2", "\U0001f7e1", "\U0001f534", "\u26ab"]:
        status_clean = status_clean.replace(emoji, "").strip()

    return VFDDiagnosticResult(
        asset_id=asset_id,
        well_id=asset_id,
        family=result.get("family", "UNKNOWN"),
        timestamp=str(result.get("timestamp", ts)),
        vfd_sts=vfd_sts,
        health_score=float(diag.get("health_score", 0.0)),
        status=status_clean,
        primary_fault=str(diag.get("primary_fault", "Unknown")),
        confidence=str(diag.get("confidence", "N/A")),
        est_time_to_trip=str(diag.get("est_time_to_trip", "Unknown")),
        description=str(diag.get("description", "")),
        action_advisory=str(diag.get("action_advisory", "")),
        root_cause_drivers=root_cause_drivers,
        dynamics=VFDDynamics(
            delta_p=float(dyn.get("delta_p", 0.0)),
            torque_proxy=float(dyn.get("torque_proxy", 0.0)),
            power_proxy_kva=float(dyn.get("power_proxy_kva", 0.0)),
            thermal_elevation=float(dyn.get("thermal_elevation", 0.0)),
            thermal_rate_hr=float(dyn.get("thermal_rate_hr", 0.0)),
            pressure_ratio=float(dyn.get("pressure_ratio", 0.0)),
        ),
        is_anomaly=bool(ml.get("is_anomaly", False)),
        anomaly_score=float(ml.get("anomaly_score", 0.0)),
        normalized_features=result.get("normalized_features", {}),
        signals_mapped=len(measurements) - len(filled),
        signals_filled=filled,
        engine_available=True,
    )
