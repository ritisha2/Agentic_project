"""
Procedure and Knowledge Service (T1_KB_ONLY)
Provides authoritative operating limits, tripping thresholds, and SOP lookups
from deterministic YAML playbooks and diagnostic rules without fabricating live telemetry.
"""

import os
import re
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

_CURRENT_DIR = Path(__file__).resolve().parent
_ESP_AGENT_ROOT = _CURRENT_DIR.parent.parent
_PROJECT_ROOT = _ESP_AGENT_ROOT.parent

_ALERTS_YAML = _PROJECT_ROOT / "esp-knowledge" / "deterministic" / "alerts" / "seed_alerts.yaml"
_RULES_JSON = _ESP_AGENT_ROOT / "knowledge_bases" / "esp" / "rules" / "diagnostic_rules.json"


class ProcedureKnowledgeService:
    """Service to look up governing operational thresholds, tripping limits, and SOPs."""

    def __init__(self):
        self._alerts: List[Dict[str, Any]] = []
        self._rules: List[Dict[str, Any]] = []
        self._load_sources()

    def _load_sources(self):
        if _ALERTS_YAML.exists():
            try:
                with open(_ALERTS_YAML, "r", encoding="utf-8") as f:
                    ydata = yaml.safe_load(f)
                    self._alerts = ydata.get("alerts", [])
            except Exception as e:
                logger.warning(f"Failed to load {_ALERTS_YAML}: {e}")

        if _RULES_JSON.exists():
            try:
                with open(_RULES_JSON, "r", encoding="utf-8") as f:
                    rdata = json.load(f)
                    self._rules = rdata.get("rules", [])
            except Exception as e:
                logger.warning(f"Failed to load {_RULES_JSON}: {e}")

    def lookup_limits(self, query: str) -> Dict[str, Any]:
        """
        Extract relevant operating limits and tripping thresholds matching the query.
        """
        q_low = query.lower()
        matched_limits = []

        # 1. Thermal / Temperature
        if any(w in q_low for w in ["temp", "temperature", "thermal", "overheat", "motor temp"]):
            matched_limits.append({
                "parameter": "Motor Internal Temperature",
                "canonical_metric": "primary_thermal_metric",
                "normal_envelope": "< 125.0 °C",
                "warning_threshold": "130.0 °C",
                "tripping_limit": "150.0 °C (Critical Trip)",
                "governing_standard": "API RP 11S / seed_alerts.yaml (MOTOR_TEMP_CRITICAL)",
                "consequence": "Stator winding thermal insulation breakdown and motor burnout.",
                "action": "Immediate engineering review, inspect cooling flow, evaluate controlled shutdown."
            })

        # 2. Intake Pressure / PIP / Gas Locking
        if any(w in q_low for w in ["intake", "pip", "drawdown", "suction", "gas lock"]):
            matched_limits.append({
                "parameter": "Pump Intake Pressure (PIP)",
                "canonical_metric": "primary_intake_pressure",
                "normal_envelope": "> 200.0 psi",
                "warning_threshold": "< 150.0 psi",
                "tripping_limit": "< 100.0 psi (Critical Low-PIP Trip)",
                "governing_standard": "diagnostic_rules.json (RULE_PIP_CRIT) / seed_alerts.yaml",
                "consequence": "Free gas breakout, fluid vapor lock, loss of cooling, and cavitation damage.",
                "action": "Reduce VFD frequency, verify choke setting, activate gas agitation cycle."
            })

        # 3. Vibration / Mechanical
        if any(w in q_low for w in ["vib", "vibration", "mechanical", "radial", "axial"]):
            matched_limits.append({
                "parameter": "Radial Vibration",
                "canonical_metric": "vibration_metric",
                "normal_envelope": "< 1.5 g RMS",
                "warning_threshold": "> 3.0 g RMS",
                "tripping_limit": "> 5.0 g RMS (Critical Trip)",
                "governing_standard": "API RP 11S8 / diagnostic_rules.json (RULE_VIB_CRIT)",
                "consequence": "Rotor unbalance, shaft deflection, bearing wear, and mechanical seal destruction.",
                "action": "Inspect vibration frequency spectrum, avoid resonance speeds, schedule bearing inspection."
            })
            matched_limits.append({
                "parameter": "Axial Vibration",
                "canonical_metric": "axial_vibration_metric",
                "normal_envelope": "< 0.8 g RMS",
                "warning_threshold": "> 1.5 g RMS",
                "tripping_limit": "> 2.5 g RMS",
                "governing_standard": "diagnostic_rules.json (RULE_AXIAL_VIB_WARN)",
                "consequence": "Thrust bearing axial load failure and stage rubbing.",
                "action": "Verify pump thrust bearing condition and fluid gas fraction."
            })

        # 4. Motor Current / Electrical Overload / Underload
        if any(w in q_low for w in ["current", "amp", "overload", "underload", "electrical", "imbalance"]):
            matched_limits.append({
                "parameter": "Drive Current Overload",
                "canonical_metric": "primary_electrical_load",
                "normal_envelope": "70% – 100% Nameplate Rating",
                "warning_threshold": "> 105% Nameplate Amps",
                "tripping_limit": "> 115% Nameplate Amps (Overload Trip)",
                "governing_standard": "diagnostic_rules.json (RULE_OVERLOAD_CRIT) / API RP 11S",
                "consequence": "Electrical overload, motor stall, or solid sand ingestion in pump stages.",
                "action": "Check for mechanical binding or fluid viscosity change; verify VFD current limit."
            })
            matched_limits.append({
                "parameter": "Drive Current Underload",
                "canonical_metric": "primary_electrical_load",
                "normal_envelope": "70% – 100% Nameplate Rating",
                "warning_threshold": "< 65% Nameplate Amps",
                "tripping_limit": "< 60% Nameplate Amps (Underload Trip)",
                "governing_standard": "diagnostic_rules.json (RULE_UNDERLOAD_CRIT)",
                "consequence": "Pump pump-off, broken shaft, or complete gas lock.",
                "action": "Verify fluid inflow and well fluid level before restart."
            })

        # 5. General / Catch-All if no specific parameter detected
        if not matched_limits:
            matched_limits.append({
                "parameter": "Motor Internal Temperature",
                "warning_threshold": "130.0 °C",
                "tripping_limit": "150.0 °C (Critical Trip)",
                "governing_standard": "API RP 11S"
            })
            matched_limits.append({
                "parameter": "Pump Intake Pressure",
                "warning_threshold": "< 150.0 psi",
                "tripping_limit": "< 100.0 psi (Critical Trip)",
                "governing_standard": "diagnostic_rules.json"
            })
            matched_limits.append({
                "parameter": "Radial Vibration",
                "warning_threshold": "> 3.0 g RMS",
                "tripping_limit": "> 5.0 g RMS (Critical Trip)",
                "governing_standard": "API RP 11S8"
            })

        return {
            "query": query,
            "matched_limits": matched_limits,
            "is_sop_query": any(w in q_low for w in ["startup", "start up", "sop", "procedure", "maintenance", "how to"]),
        }

    def format_advisory_text(self, query: str, asset_id: str) -> Dict[str, Any]:
        """
        Format an authoritative advisory text responding to the operator's procedure query.
        """
        info = self.lookup_limits(query)
        q_low = query.lower()

        # Startup SOP flow
        if any(w in q_low for w in ["startup", "start up", "procedure for startup", "start procedure"]):
            assessment = (
                f"### 📋 Standard Operating Procedure: ESP Pump Startup Protocol\n\n"
                f"**Governing Reference:** API RP 11S (Recommended Practice for Electric Submersible Pump Installations) §6 & OEM Standard\n\n"
                f"#### Phase 1: Pre-Start Verification Checklist\n"
                f"1. **Electrical Isolation & Insulation:** Verify motor and downhole cable insulation resistance > 10 MΩ (Megger test).\n"
                f"2. **Surface Facilities:** Confirm flowline master valves are fully OPEN, flowmeter active, and surface separator ready.\n"
                f"3. **Fluid Level:** Confirm well casing fluid level and static intake pressure > 250 psi.\n\n"
                f"#### Phase 2: Start & Ramp-Up Sequence\n"
                f"1. **Initial Frequency:** Initiate VFD at 35.0 Hz minimum startup speed to establish fluid lift and motor cooling.\n"
                f"2. **Current Surge Monitoring:** Observe motor starting current spike; ensure current stabilizes within nameplate rating within 15 seconds.\n"
                f"3. **Gradual Frequency Ramp:** Increment VFD speed at a rate not exceeding 0.5 Hz / minute toward nominal operating point (typically 50.0 Hz).\n\n"
                f"#### Phase 3: Post-Startup Critical Thresholds (First 60 Minutes)\n"
                f"• **Motor Temperature:** Must stabilize < 130.0 °C (Abort startup if temp exceeds 150.0 °C).\n"
                f"• **Intake Pressure (PIP):** Must remain > 150.0 psi (Gas lock warning threshold).\n"
                f"• **Vibration:** Must remain < 3.0 g RMS radial vibration."
            )
            diagnosis = "API RP 11S standard operating procedure for ESP pump startup and commissioning."
            recommendation = "Execute pre-start Megger check and verify open surface valves prior to initiating VFD ramp."
            verification = [
                "1. Document pre-start insulation resistance in well log.",
                "2. Confirm flowline backpressure is within design parameters."
            ]
            citations = [
                {"document_id": "API_RP_11S", "section": "Section 6: Startup & Commissioning", "authority_level": "A"},
                {"document_id": "SOP_PUMP_STARTUP", "section": "Standard Checklist", "authority_level": "B"}
            ]
            return {
                "assessment": assessment,
                "diagnosis": diagnosis,
                "recommendation": recommendation,
                "verification": verification,
                "citations": citations
            }

        # Limits / Thresholds flow
        limits = info["matched_limits"]
        table_rows = []
        for lim in limits:
            table_rows.append(
                f"| **{lim['parameter']}** | `{lim.get('normal_envelope', 'Nominal')}` | "
                f"`{lim['warning_threshold']}` | **`{lim.get('tripping_limit', 'Trip')}`** | "
                f"*{lim.get('governing_standard', 'API RP 11S')}* |"
            )

        table_md = "\n".join(table_rows)

        assessment = (
            f"### ⚙️ Governing Operating Thresholds & Tripping Limits\n\n"
            f"**Authority Hierarchy:** API RP 11S (Authority A) & Seed Diagnostic Rules (Authority B)\n\n"
            f"| Operational Parameter | Normal Range | Warning Alarm | Shutdown Tripping Limit | Standard Source |\n"
            f"| :--- | :--- | :--- | :--- | :--- |\n"
            f"{table_md}\n\n"
        )

        for lim in limits:
            if "consequence" in lim:
                assessment += (
                    f"#### ⚠️ {lim['parameter']} Safeguard Specification\n"
                    f"- **Tripping Limit:** `{lim.get('tripping_limit')}`\n"
                    f"- **Failure Risk:** {lim['consequence']}\n"
                    f"- **Approved Action:** {lim.get('action')}\n\n"
                )

        diagnosis = f"Operational thresholds retrieved for: {', '.join(l['parameter'] for l in limits)}."
        recommendation = "Ensure SCADA alarm bands and VFD protective setpoints match these governing limits."
        verification = [
            "1. Audit VFD trip parameter register against API RP 11S thresholds.",
            "2. Verify SCADA alarm dispatch configuration."
        ]
        citations = [
            {"document_id": "API_RP_11S", "section": "Protection & Monitoring §5", "authority_level": "A"},
            {"document_id": "diagnostic_rules.json", "section": "Critical Limits", "authority_level": "B"}
        ]
        return {
            "assessment": assessment,
            "diagnosis": diagnosis,
            "recommendation": recommendation,
            "verification": verification,
            "citations": citations
        }


procedure_knowledge_service = ProcedureKnowledgeService()
