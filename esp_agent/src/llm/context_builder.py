"""
Compact Context Builder — Phase 10: LLM Layer Architecture
Grounded in ESP APM LLM Architecture Design §2

Critical for small (4B) models: transforms raw telemetry arrays and large evidence
dumps into a compact, high-density JSON context window.

A 4B parameter model cannot reason over 10,000 raw telemetry points.
This builder compresses inputs to a single structured JSON object under ~800 tokens.

Output format:
{
  "asset_id": "FS-031",
  "objective": "production_decline_analysis",
  "telemetry_summary": {
    "flow": {"current": 735.7, "trend": "declining", "qod": "good"},
    "intake_pressure": {"current": 236.5, "trend": "stable"},
    ...
  },
  "engineering": {"pump_delta_p": 1647.2, "frequency_hz": 46.06},
  "ml_scores": {"degradation_probability": 0.72},
  "frozen_evidence_ids": ["EV-001", "EV-007"],
  "specialist_findings": ["Finding A", "Finding B"],
  "safety_constraints": ["ADVISORY-ONLY — no direct actuator commands"],
  "conflicts_summary": ["ML fault confidence disagrees with physics model at p=0.15"]
}
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Max evidence items to include in compact context (prevents token overflow)
MAX_EVIDENCE_REFS = 8
MAX_SPECIALIST_FINDINGS = 6
MAX_CONFLICT_SUMMARY = 4


class CompactContextBuilder:
    """
    Transforms raw AgentState context into a compact, Qwen3 4B-safe JSON payload.
    
    LangGraph Supervisor
          ↓
    CompactContextBuilder.build(state)
          ↓
    compact_context: Dict (< 800 tokens when serialised)
          ↓
    LLM Adapter → Prompt Builder → Qwen3 4B
    """

    def build(
        self,
        asset_id: str,
        objective_id: str,
        telemetry: Optional[Dict[str, Any]] = None,
        engineering: Optional[Dict[str, Any]] = None,
        model_outputs: Optional[Dict[str, Any]] = None,
        specialist_results: Optional[List[Dict[str, Any]]] = None,
        evidence_refs: Optional[List[str]] = None,
        safety_constraints: Optional[List[str]] = None,
        conflicts: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build a compact context dict from all available supervisor state components.
        """
        compact: Dict[str, Any] = {
            "asset_id": asset_id,
            "objective": objective_id,
        }

        # --- Telemetry Summary ---
        if telemetry:
            compact["telemetry_summary"] = self._compress_telemetry(telemetry)

        # --- Engineering Snapshot ---
        if engineering:
            compact["engineering"] = self._compress_engineering(engineering)

        # --- ML/Model Scores ---
        if model_outputs:
            compact["ml_scores"] = self._compress_model_outputs(model_outputs)

        # --- Specialist Findings ---
        if specialist_results:
            findings = []
            for res in specialist_results:
                for f in res.get("findings", [])[:2]:  # max 2 per specialist
                    findings.append(f)
            compact["specialist_findings"] = findings[:MAX_SPECIALIST_FINDINGS]

        # --- Evidence References ---
        if evidence_refs:
            compact["frozen_evidence_ids"] = evidence_refs[:MAX_EVIDENCE_REFS]

        # --- Safety Constraints ---
        if safety_constraints:
            compact["safety_constraints"] = safety_constraints[:3]

        # --- Conflict Summaries ---
        if conflicts:
            compact["conflicts_summary"] = self._compress_conflicts(conflicts)

        logger.debug(
            f"CompactContextBuilder: built compact context for {asset_id}/{objective_id} "
            f"with keys: {list(compact.keys())}"
        )
        return compact

    def build_from_agent_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convenience builder that extracts fields directly from a LangGraph AgentState dict.
        """
        ctx = state.get("context", {})
        return self.build(
            asset_id=state.get("request", {}).get("asset_id", "UNKNOWN"),
            objective_id=state.get("run", {}).get("objective_id", "UNKNOWN"),
            telemetry=ctx.get("telemetry"),
            engineering=ctx.get("engineering"),
            model_outputs=ctx.get("models"),
            specialist_results=state.get("specialist_results", []),
            evidence_refs=state.get("evidence_refs", []),
            safety_constraints=state.get("safety_state", {}).get("blocked_actions", []),
            conflicts=[c.model_dump() if hasattr(c, "model_dump") else c
                       for c in state.get("conflicts", [])],
        )

    # ------------------------------------------------------------------
    # Internal compression helpers
    # ------------------------------------------------------------------

    def _compress_telemetry(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reduce raw telemetry dict to key signal summaries with trend direction.
        Input: flat dict of signal_name -> value (may include lists/arrays).
        Output: compact dict of signal_name -> {current, trend, qod}
        """
        SIGNAL_MAP = {
            "flow_rate": "flow",
            "liquid_rate": "flow",
            "intake_pressure": "intake_pressure",
            "pip": "intake_pressure",
            "discharge_pressure": "discharge_pressure",
            "pdp": "discharge_pressure",
            "motor_temperature": "motor_temp",
            "motor_temp": "motor_temp",
            "current": "drive_current",
            "drive_current": "drive_current",
            "frequency": "frequency_hz",
            "vibration": "vibration",
            "gor": "gor",
            "wc": "water_cut",
        }

        summary: Dict[str, Any] = {}
        for raw_key, val in raw.items():
            canonical = SIGNAL_MAP.get(raw_key.lower(), raw_key.lower())
            if isinstance(val, dict):
                # Pass through pre-computed statistical summaries
                summary[canonical] = {
                    k: (round(v, 4) if isinstance(v, float) else v)
                    for k, v in val.items()
                }
            elif isinstance(val, (int, float)):
                summary[canonical] = {"current": round(float(val), 2), "trend": "unknown"}
            elif isinstance(val, list) and len(val) >= 2:
                # Derive simple trend from first and last values
                first, last = float(val[0]), float(val[-1])
                if last < first * 0.95:
                    trend = "declining"
                elif last > first * 1.05:
                    trend = "rising"
                else:
                    trend = "stable"
                summary[canonical] = {"current": round(last, 2), "trend": trend}

        return summary

    def _compress_engineering(self, eng: Dict[str, Any]) -> Dict[str, Any]:
        """Keep key engineering KPIs and equipment specifications relevant to diagnosis."""
        keep_numeric = [
            "tdh_ft", "pump_delta_p", "bep_flow_rate", "bep_deviation_pct",
            "frequency_hz", "frequency", "efficiency_pct", "motor_hp",
            "nameplate_amps", "bep_bpd", "be_point_bpd", "installation_depth_ft",
            "motor_rating_hp", "nameplate_current_amps"
        ]
        keep_string = ["pump_model", "asset_id", "status", "asset_type"]

        res: Dict[str, Any] = {}
        for k, v in eng.items():
            if k in keep_numeric and isinstance(v, (int, float)):
                res[k] = round(float(v), 2)
            elif k in keep_string and isinstance(v, str):
                res[k] = v
            elif isinstance(v, (int, float, str)):
                res[k] = round(float(v), 2) if isinstance(v, float) else v
        return res

    def _compress_model_outputs(self, models: Dict[str, Any]) -> Dict[str, Any]:
        """Compress ML model outputs to key probability scores."""
        keep = ["degradation_probability", "anomaly_score", "risk_24h",
                "confidence", "predicted_fault_class", "health_index"]
        result = {}
        for k, v in models.items():
            if k in keep:
                result[k] = round(float(v), 3) if isinstance(v, (int, float)) else v
        return result

    def _compress_conflicts(self, conflicts: List[Any]) -> List[str]:
        """Summarise conflicts as brief strings for the model."""
        summaries = []
        for c in conflicts[:MAX_CONFLICT_SUMMARY]:
            if isinstance(c, dict):
                ctype = c.get("conflict_type", "CONFLICT")
                auth = c.get("authority_comparison", "")
                summaries.append(f"{ctype}: {auth}"[:120])
            elif hasattr(c, "conflict_type"):
                summaries.append(f"{c.conflict_type}: {c.authority_comparison}"[:120])
            else:
                summaries.append(str(c)[:80])
        return summaries
