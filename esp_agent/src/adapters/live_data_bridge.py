"""
LiveDataBridge — HTTP Adapter connecting esp_agent to cced_esp backend (:8000)
Routes live telemetry, ML assessments, fleet asset context, and time-series data
from the cced_esp production stack into the LangGraph Supervisor graph nodes.

Zero folder moves. Zero code duplication. Pure routing adapter.
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# cced_esp backend base URL — configurable via env, defaults to local dev port
CCED_ESP_BASE_URL = os.getenv("CCED_ESP_BACKEND_URL", "http://127.0.0.1:8000")

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False
    logger.warning("[LiveDataBridge] httpx not installed. Install with: pip install httpx")


class LiveDataBridge:
    """
    Lightweight HTTP client bridge: esp_agent → cced_esp backend (:8000).
    All methods degrade gracefully — return None/empty if cced_esp is unreachable.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or CCED_ESP_BASE_URL).rstrip("/")
        self._available: Optional[bool] = None
        self._timeout = 4.0  # seconds

    # ─────────────────────────────────────────────────────────────────────────
    # Connectivity
    # ─────────────────────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Check if cced_esp backend is reachable."""
        if not _HTTPX_AVAILABLE:
            return False
        try:
            r = httpx.get(f"{self.base_url}/api/status", timeout=2.0)
            self._available = r.status_code == 200
        except Exception:
            self._available = False
        return self._available

    def _get(self, path: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Internal GET helper. Returns parsed JSON dict or None on any error."""
        if not _HTTPX_AVAILABLE:
            return None
        try:
            r = httpx.get(
                f"{self.base_url}{path}",
                params=params or {},
                timeout=self._timeout
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.debug(f"[LiveDataBridge] GET {path} failed: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Telemetry
    # ─────────────────────────────────────────────────────────────────────────

    def get_latest_telemetry(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch latest telemetry record for the asset from cced_esp SQLite ledger.
        Maps to:  GET /api/telemetry?asset_id={asset_id}&limit=1
        Returns a dict with sensor fields: flow_rate_bpd, intake_pressure_psi,
        pressure_psi, temperature_c, vibration_g, motor_current_a,
        motor_voltage_v, frequency_hz, scenario, operating_state.
        """
        data = self._get("/api/telemetry", params={"asset_id": asset_id, "limit": 1})
        if not data:
            data = self._get("/api/telemetry", params={"well_id": asset_id, "limit": 1})
        records = (data or {}).get("records", [])
        return records[0] if records else None

    def get_telemetry_as_agent_dict(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns telemetry in the exact dict shape the Supervisor graph expects:
        {motor_temperature, intake_pressure, discharge_pressure, flow_rate,
         drive_current_average, frequency, vibration_x}
        """
        row = self.get_latest_telemetry(asset_id)
        if not row:
            return None
        return {
            "motor_temperature": float(row.get("temperature_c") or 0.0),
            "intake_pressure":   float(row.get("intake_pressure_psi") or 0.0),
            "discharge_pressure": float(row.get("pressure_psi") or
                                        row.get("discharge_pressure_psi") or 0.0),
            "flow_rate":          float(row.get("flow_rate_bpd") or 0.0),
            "drive_current_average": float(row.get("motor_current_a") or 0.0),
            "frequency":          float(row.get("frequency_hz") or 0.0),
            "vibration_x":        float(row.get("vibration_g") or 0.0),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # ML Assessment (Health Index, Fault Classification, Anomaly Score)
    # ─────────────────────────────────────────────────────────────────────────

    def get_ml_assessment(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch real-time ML health assessment from cced_esp unified inference pipeline.
        Maps to:  GET /api/esp/assets/{asset_id}/health-index
        Returns dict with: health_index (0-100), status, predicted_fault, confidence,
        anomaly_score, risk_level, rul_days.
        """
        return self._get(f"/api/esp/assets/{asset_id}/health-index")

    def get_model_output_payload(self, asset_id: str) -> Optional[Any]:
        """
        Fetch ML assessment and wrap into normalized ModelOutputPayload domain contract (§11).
        """
        raw = self.get_ml_assessment(asset_id)
        if not raw or "prediction" not in raw:
            return None
        
        try:
            from datetime import datetime
            from src.schemas.contracts import (
                ModelOutputPayload, AnomalyResultPayload, FailurePredictionPayload,
                FaultDiagnosisPayload, HealthIndexPayload
            )

            p = raw["prediction"]
            now = datetime.utcnow().isoformat() + "Z"
            hi = float(p.get("health_index", 95.0))
            fault_class = p.get("status", "NORMAL_OPERATION")
            conf = round(hi / 100.0, 2)

            return ModelOutputPayload(
                asset_id=asset_id,
                timestamp=now,
                rules=None,
                anomaly=AnomalyResultPayload(
                    asset_id=asset_id,
                    timestamp=now,
                    anomaly_score=round(1.0 - conf, 2),
                    status="ANOMALOUS" if conf < 0.8 else "NORMAL",
                    contributing_signals=["intake_pressure", "motor_temperature"]
                ),
                failure=FailurePredictionPayload(
                    asset_id=asset_id,
                    timestamp=now,
                    risk_24h=round(1.0 - conf, 2),
                    risk_72h=round(min(1.0, (1.0 - conf) * 1.3), 2),
                    risk_7d=round(min(1.0, (1.0 - conf) * 1.8), 2),
                    rul_hours=float(int(p.get("rul_days", 45)) * 24),
                    primary_failure_mode=fault_class
                ),
                fault=FaultDiagnosisPayload(
                    asset_id=asset_id,
                    timestamp=now,
                    predicted_fault_class=fault_class,
                    confidence=conf,
                    top_root_causes=[fault_class],
                    remediation_action=f"Inspect asset {asset_id} for {fault_class}"
                ),
                health=HealthIndexPayload(
                    asset_id=asset_id,
                    timestamp=now,
                    health_index=hi,
                    status="HEALTHY" if hi > 85 else ("WARNING" if hi > 60 else "CRITICAL")
                )
            )
        except Exception as ex:
            logger.warning(f"[LiveDataBridge] Error mapping ModelOutputPayload for '{asset_id}': {ex}")
            return None

    def get_engineering_context(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch real-time TDH and operating envelope from cced_esp.
        Maps to: GET /api/esp/assets/{asset_id}/envelope
        Returns dict with TDH, BEP deviation, operating window limits.
        """
        return self._get(f"/api/esp/assets/{asset_id}/envelope")

    # ─────────────────────────────────────────────────────────────────────────
    # VFD Diagnostic (ESP_APM_models.WellDiagnosticEngine, live MQTT-fed)
    # ─────────────────────────────────────────────────────────────────────────

    def get_vfd_diagnostic(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch the latest ESP_APM_models diagnosis for this well — the 14-signal VFD
        model, fed live off the real MQTT broker via cced_esp's vfd_diagnostic_service.
        Maps to: GET /api/vfd/diagnostics/{asset_id}
        Returns dict with: diagnostic {primary_fault, confidence, health_score, status,
        est_time_to_trip, description, action_advisory, root_cause_drivers}, dynamics
        {delta_p, torque_proxy, power_proxy_kva, thermal_elevation, ...}, ml_anomaly
        {is_anomaly, anomaly_probability}, raw_measurements (the 14 VFD signals).
        Returns None if the well has no diagnosis yet or cced_esp is unreachable —
        never fabricated; distinct from get_ml_assessment() (the legacy health-index path).
        """
        return self._get(f"/api/vfd/diagnostics/{asset_id}")

    def get_all_vfd_diagnostics(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch the latest ESP_APM_models diagnosis for every well seen so far.
        Maps to: GET /api/vfd/diagnostics
        Returns {well_id: diagnosis_dict, ...}; empty dict if unreachable/none yet.
        """
        data = self._get("/api/vfd/diagnostics")
        return (data or {}).get("wells", {})

    # ─────────────────────────────────────────────────────────────────────────
    # Fleet Asset Registry
    # ─────────────────────────────────────────────────────────────────────────

    def get_fleet_assets(self) -> List[Dict[str, Any]]:
        """
        Fetch all 26 canonical assets with live health index and pump specs.
        Maps to: GET /api/esp/assets
        Returns list of asset dicts.
        """
        data = self._get("/api/esp/assets")
        return (data or {}).get("assets", [])

    def get_asset_summary(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch summarised asset data row from fleet list for a specific asset.
        Includes pump_family, rated_bpd, rated_hp, health_index.
        """
        assets = self.get_fleet_assets()
        for a in assets:
            if a.get("asset_id") == asset_id or a.get("well_id") == asset_id:
                return a
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Time-Series Chart Data (for Generative UI Plotly Charts)
    # ─────────────────────────────────────────────────────────────────────────

    def get_timeseries(
        self,
        asset_id: str,
        limit: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch historical time-series telemetry for Plotly chart rendering.
        Maps to: GET /api/analytics/timeseries?asset_id={id}&limit={limit}
        Returns dict with 'points' list containing: timestamp, flow_rate_bpd,
        intake_pressure_psi, pressure_psi, temperature_c, motor_current_a.
        """
        return self._get(
            "/api/analytics/timeseries",
            params={"asset_id": asset_id, "limit": limit}
        )

    def build_plotly_trace(self, asset_id: str) -> List[Dict[str, Any]]:
        """
        Convert cced_esp time-series into Plotly-compatible trace objects
        ready for the generative_ui stream event.
        Falls back to empty list if backend is unreachable.
        """
        data = self.get_timeseries(asset_id, limit=24)
        points = (data or {}).get("points", [])
        if not points:
            try:
                from src.tools.fetch_telemetry import get_history_window_tool
                hist = get_history_window_tool(asset_id=asset_id, limit=30)
                traces = []
                for sig in hist.series:
                    sig_name = getattr(sig, "signal", getattr(sig, "signal_name", "unknown"))
                    pts = getattr(sig, "points", [])
                    if not pts:
                        continue
                    xs = [str(p.timestamp)[-8:-3] if len(str(p.timestamp)) >= 8 else str(p.timestamp) for p in pts]
                    ys = [float(p.value) for p in pts]

                    if sig_name == "flow_rate":
                        traces.append({
                            "x": xs, "y": ys, "type": "scatter", "mode": "lines+markers",
                            "name": f"Flow Rate ({sig.unit})", "line": {"color": "#ef4444", "width": 2.5}
                        })
                    elif "pressure" in sig_name:
                        traces.append({
                            "x": xs, "y": ys, "type": "scatter", "mode": "lines",
                            "name": f"{sig_name.replace('_', ' ').title()} ({sig.unit})",
                            "yaxis": "y2", "line": {"color": "#0284c7" if "intake" in sig_name else "#8b5cf6", "width": 2, "dash": "dot"}
                        })
                    elif sig_name == "motor_temperature":
                        traces.append({
                            "x": xs, "y": ys, "type": "scatter", "mode": "lines",
                            "name": f"Motor Temp ({sig.unit})",
                            "yaxis": "y2", "line": {"color": "#f59e0b", "width": 1.5, "dash": "dash"}
                        })
                if traces:
                    return traces
            except Exception as e:
                logger.debug(f"[LiveDataBridge] Local DB trace fallback failed: {e}")
            return []

        timestamps = [p.get("timestamp", "")[-8:-3] for p in points]  # HH:MM
        flow      = [float(p.get("flow_rate_bpd")      or 0) for p in points]
        pip       = [float(p.get("intake_pressure_psi") or 0) for p in points]
        temp      = [float(p.get("temperature_c")       or 0) for p in points]

        traces = []
        if any(v > 0 for v in flow):
            traces.append({
                "x": timestamps, "y": flow,
                "type": "scatter", "mode": "lines+markers",
                "name": "Production Rate (BPD)",
                "line": {"color": "#ef4444", "width": 2.5}
            })
        if any(v > 0 for v in pip):
            traces.append({
                "x": timestamps, "y": pip,
                "type": "scatter", "mode": "lines",
                "name": "Intake Pressure (PSI)",
                "yaxis": "y2",
                "line": {"color": "#0284c7", "width": 2, "dash": "dot"}
            })
        if any(v > 0 for v in temp):
            traces.append({
                "x": timestamps, "y": temp,
                "type": "scatter", "mode": "lines",
                "name": "Motor Temp (°C)",
                "yaxis": "y2",
                "line": {"color": "#f59e0b", "width": 1.5, "dash": "dash"}
            })
        return traces


    # ─────────────────────────────────────────────────────────────────────────
    # Dedicated Historian REST Service (historian.txt §7, §8)
    # ─────────────────────────────────────────────────────────────────────────

    def get_available_signals(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Query available historian signals for asset.
        Maps to: GET /api/v1/historian/{asset_id}/available-signals
        """
        return self._get(f"/api/v1/historian/{asset_id}/available-signals")

    def get_historian_window(
        self,
        asset_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        signals: Optional[List[str]] = None,
        aggregation: str = "raw",
        limit: int = 1000
    ) -> Optional[Dict[str, Any]]:
        """
        Query canonical time-series window from dedicated Historian Service.
        Maps to: GET /api/v1/historian/{asset_id}/window
        """
        params = {
            "aggregation": aggregation,
            "limit": limit
        }
        if start_time:
            params["start"] = start_time
        if end_time:
            params["end"] = end_time
        if signals:
            params["signals"] = ",".join(signals) if isinstance(signals, list) else str(signals)

        return self._get(f"/api/v1/historian/{asset_id}/window", params=params)


# Global singleton — shared across all bff_routes and graph node calls
live_bridge = LiveDataBridge()
