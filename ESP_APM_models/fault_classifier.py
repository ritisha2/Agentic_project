"""
13-Fault Diagnostic Classification Engine Component
===================================================
Physics-informed multi-criteria evaluation engine for diagnosing the 13 specific ESP failure modes:
1. Dry-Well Pump Off
2. Blocked Intake
3. Scale or Pump Wear
4. Sand Ingestion
5. Bearing Degradation
6. High Viscosity Cold Start
7. High Backpressure
8. Open Choke
9. Undervoltage
10. Phase Imbalance
11. Motor Overload
12. Power Loss
13. Sensor Drift
"""

from typing import Dict, List, Tuple, Optional, Any


FAULT_DEFINITIONS = {
    "Dry-Well Pump Off": {
        "severity": "CRITICAL",
        "description": "Fluid level in well has dropped below pump intake; pump running dry without fluid cooling.",
        "action": "Shut down or reduce frequency immediately to prevent motor burnout; allow well fluid recovery."
    },
    "Blocked Intake": {
        "severity": "CRITICAL",
        "description": "Debris, scale, or asphaltene plugging pump intake screen; fluid flow choked.",
        "action": "Backwash intake screen, adjust surface choke, or pull ESP for mechanical cleanout."
    },
    "Scale or Pump Wear": {
        "severity": "WARNING",
        "description": "Impeller stage erosion or mineral scale build-up causing hydraulic head degradation.",
        "action": "Schedule chemical scale descaling treatment or plan pump stage replacement."
    },
    "Sand Ingestion": {
        "severity": "CRITICAL",
        "description": "Solids/sand production causing impeller erosion, friction torque surges, and erratic vibration.",
        "action": "Flush well with clean fluid; install sand screens or downhole desander."
    },
    "Bearing Degradation": {
        "severity": "CRITICAL",
        "description": "Radial or thrust bearing mechanical wear causing high vibration and internal friction heating.",
        "action": "Plan ESP changeout before catastrophic mechanical shaft seizure occurs."
    },
    "High Viscosity Cold Start": {
        "severity": "WARNING",
        "description": "High crude oil viscosity/emulsion at cold start causing extreme motor starting torque and current.",
        "action": "Soft-ramp VFD frequency slowly; circulate hot oil or diluent to reduce crude viscosity."
    },
    "High Backpressure": {
        "severity": "WARNING",
        "description": "Flowline blockage, closed surface valves, or hydrate restriction elevating discharge pressure.",
        "action": "Check surface choke line, separator inlet, and manifold valves for restrictions."
    },
    "Open Choke": {
        "severity": "WARNING",
        "description": "Surface choke open too wide causing runout flow, high motor amperage, and low head.",
        "action": "Trim surface choke orifice to restore pump operating backpressure."
    },
    "Undervoltage": {
        "severity": "CRITICAL",
        "description": "Surface power supply/transformer voltage sag causing elevated motor current draw and heating.",
        "action": "Check surface transformer tap settings and power grid stability; balance bus voltage."
    },
    "Phase Imbalance": {
        "severity": "CRITICAL",
        "description": "Voltage or current unbalance across phases creating reverse magnetic fields, overheating, and vibration.",
        "action": "Perform downhole cable insulation Megger test and check surface VFD output phase balance."
    },
    "Motor Overload": {
        "severity": "CRITICAL",
        "description": "Motor operating continuously above rated nameplate amperage; imminent thermal trip.",
        "action": "Reduce VFD frequency by 3–5 Hz immediately to shed electrical load and cool motor."
    },
    "Power Loss": {
        "severity": "CRITICAL",
        "description": "Total power interruption or automated VFD trip; pump stopped.",
        "action": "Investigate surface breaker/VFD fault code before attempting restart."
    },
    "Sensor Drift": {
        "severity": "WATCHLIST",
        "description": "Sensor output flatlined, stuck, or drifted to non-physical range.",
        "action": "Recalibrate downhole gauge telemetry or replace surface pressure/temperature transmitter."
    }
}


class FaultClassificationEngine:
    """
    Diagnostic Classification Engine:
    Evaluates normalized features, raw values, and physical dynamics to classify the 13 specific well faults.
    """

    @staticmethod
    def diagnose(
        well_id: str,
        norm_data: Dict[str, float],
        raw_data: Dict[str, float],
        dynamics: Dict[str, float],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates physical and statistical evidence for all 13 failure modes.
        """
        sensors_prof = profile.get("sensors", {})

        # Raw values
        inp = raw_data.get("Inp bar/psi", 100.0)
        disch = raw_data.get("Disch pr. Bar/psi", 1000.0)
        amps = raw_data.get("VSD Amps/Load", 50.0)
        volt = raw_data.get("Volt", 400.0)
        freq = raw_data.get("Frequency", 50.0)
        vib = raw_data.get("Vibration G's-Vx", 0.1)
        leak = raw_data.get("Leak Current Ct", 5.0)
        m_temp = raw_data.get("Motor temp °C", 70.0)
        i_temp = raw_data.get("Int temp °C", 50.0)
        whp = raw_data.get("WHP (PSI)", 50.0)
        flp = raw_data.get("FLP (PSI)", 50.0)
        ap = raw_data.get("AP (PSI)", 10.0)
        vfd_sts = raw_data.get("VFD STS", 1.0)

        # Dynamics
        delta_p = dynamics.get("delta_p", 900.0)
        torque = dynamics.get("torque_proxy", 1.0)
        dt_slope = dynamics.get("thermal_rate_hr", 0.0)

        # Baseline references
        amps_med = sensors_prof.get("VSD Amps/Load", {}).get("median", 50.0)
        disch_med = sensors_prof.get("Disch pr. Bar/psi", {}).get("median", 1500.0)
        inp_med = sensors_prof.get("Inp bar/psi", {}).get("median", 400.0)
        volt_med = sensors_prof.get("Volt", {}).get("median", 400.0)
        vib_med = sensors_prof.get("Vibration G's-Vx", {}).get("median", 0.1)
        whp_med = sensors_prof.get("WHP (PSI)", {}).get("median", 50.0)
        flp_med = sensors_prof.get("FLP (PSI)", {}).get("median", 45.0)
        m_temp_med = sensors_prof.get("Motor temp °C", {}).get("median", 70.0)
        head_med = max(200.0, disch_med - inp_med)

        scores = {}
        drivers = {}

        # -------------------------------------------------------------
        # 1. Power Loss (All electrical params drop to zero)
        # -------------------------------------------------------------
        if volt < 20.0 and amps < 2.0 and freq < 5.0:
            scores["Power Loss"] = 0.98
            drivers["Power Loss"] = [("Volt", "-95% (0 V)"), ("VSD Amps/Load", "-95% (0 A)"), ("Frequency", "-90% (0 Hz)")]
        else:
            scores["Power Loss"] = 0.0

        # -------------------------------------------------------------
        # 2. Dry-Well Pump Off (Intake collapsed, underload amps, temp rise)
        # -------------------------------------------------------------
        dry_score = 0.0
        dry_drivers = []
        if inp < 0.25 * max(1.0, inp_med) and vfd_sts > 0.5:
            dry_score += 0.45
            dry_drivers.append(("Inp bar/psi", f"-{int((1 - inp/max(1.0, inp_med))*100)}% (Fluid level lost)"))
        if amps < 0.55 * max(1.0, amps_med) and vfd_sts > 0.5:
            dry_score += 0.35
            dry_drivers.append(("VSD Amps/Load", f"-{int((1 - amps/max(1.0, amps_med))*100)}% (Underload dry run)"))
        if m_temp > (m_temp_med + 12.0) or dt_slope > 1.5:
            dry_score += 0.20
            dry_drivers.append(("Motor temp °C", f"{m_temp:.1f}°C (Cooling lost)"))
        scores["Dry-Well Pump Off"] = min(0.99, dry_score) if dry_score >= 0.45 else 0.0
        drivers["Dry-Well Pump Off"] = dry_drivers

        # -------------------------------------------------------------
        # 3. Blocked Intake (Intake collapse + discharge drop + delta_p collapse)
        # -------------------------------------------------------------
        block_score = 0.0
        block_drivers = []
        if inp < 0.20 * max(1.0, inp_med) and vfd_sts > 0.5:
            block_score += 0.40
            block_drivers.append(("Inp bar/psi", f"{inp:.1f} PSI (Suction starved)"))
        if disch < 0.35 * max(1.0, disch_med) and delta_p < 200.0:
            block_score += 0.45
            block_drivers.append(("Disch pr. Bar/psi", f"{disch:.1f} PSI (No fluid discharge)"))
        if amps < 0.65 * max(1.0, amps_med):
            block_score += 0.15
            block_drivers.append(("VSD Amps/Load", "Underloaded pump (no flow)"))
        scores["Blocked Intake"] = min(0.96, block_score) if block_score >= 0.50 else 0.0
        drivers["Blocked Intake"] = block_drivers

        # -------------------------------------------------------------
        # 4. Scale or Pump Wear (Loss of Head/DeltaP at constant speed, normal intake)
        # -------------------------------------------------------------
        wear_score = 0.0
        wear_drivers = []
        if freq >= 42.0 and delta_p < 0.65 * head_med and inp > 0.40 * max(1.0, inp_med) and whp > 10.0:
            wear_score = 0.95
            wear_drivers.append(("Disch pr. Bar/psi", f"DeltaP {delta_p:.0f} PSI (-{int((1-delta_p/head_med)*100)}% head loss)"))
            wear_drivers.append(("Frequency", f"Steady {freq:.1f} Hz (Impeller/stage degradation)"))
        scores["Scale or Pump Wear"] = wear_score
        drivers["Scale or Pump Wear"] = wear_drivers

        # -------------------------------------------------------------
        # 5. Sand Ingestion (Abrasive torque spikes + high vibration surges)
        # -------------------------------------------------------------
        sand_score = 0.0
        sand_drivers = []
        if (vib >= 0.28 or vib > 1.6 * max(0.05, vib_med)) and amps > 1.15 * max(1.0, amps_med):
            sand_score = 0.96
            sand_drivers.append(("Vibration G's-Vx", f"{vib:.2f} G (Abrasive turbulence)"))
            sand_drivers.append(("VSD Amps/Load", f"{amps:.1f} A (+{int((amps/amps_med - 1)*100)}% solids drag)"))
        scores["Sand Ingestion"] = sand_score
        drivers["Sand Ingestion"] = sand_drivers

        # -------------------------------------------------------------
        # 6. Bearing Degradation (Severe vibration + motor friction heat, normal amps)
        # -------------------------------------------------------------
        bear_score = 0.0
        bear_drivers = []
        if vib >= 0.35 and (m_temp > 82.0 or m_temp > m_temp_med + 10.0) and amps <= 1.25 * max(1.0, amps_med):
            bear_score = 0.97
            bear_drivers.append(("Vibration G's-Vx", f"{vib:.2f} G (Severe bearing wear > 0.35 G)"))
            bear_drivers.append(("Motor temp °C", f"{m_temp:.1f}°C (Bearing friction heating)"))
        scores["Bearing Degradation"] = bear_score
        drivers["Bearing Degradation"] = bear_drivers

        # -------------------------------------------------------------
        # 7. High Viscosity Cold Start (Low speed + extreme starting torque/amps)
        # -------------------------------------------------------------
        cold_score = 0.0
        cold_drivers = []
        if freq < 38.0 and (amps > 1.15 * max(1.0, amps_med) or torque > 1.30 * (amps_med / 50.0)) and (i_temp < 35.0 or m_temp < 50.0):
            cold_score = 0.95
            cold_drivers.append(("VSD Amps/Load", f"{amps:.1f} A at {freq:.1f} Hz (Extreme starting torque)"))
            cold_drivers.append(("Int temp °C", f"{i_temp:.1f}°C (Cold heavy crude/emulsion)"))
        scores["High Viscosity Cold Start"] = cold_score
        drivers["High Viscosity Cold Start"] = cold_drivers

        # -------------------------------------------------------------
        # 8. High Backpressure (High FLP/WHP forcing discharge up relative to well baseline)
        # -------------------------------------------------------------
        back_score = 0.0
        back_drivers = []
        if (flp > 1.35 * max(20.0, flp_med) or whp > 1.35 * max(20.0, whp_med)) and disch > 1.20 * max(100.0, disch_med):
            back_score = 0.93
            back_drivers.append(("FLP (PSI)", f"{flp:.1f} PSI (Flowline backpressure restricted)"))
            back_drivers.append(("Disch pr. Bar/psi", f"{disch:.1f} PSI (Discharge forced up)"))
        scores["High Backpressure"] = back_score
        drivers["High Backpressure"] = back_drivers

        # -------------------------------------------------------------
        # 9. Open Choke (Choke wide open -> WHP near 0, low discharge, high runout amps)
        # -------------------------------------------------------------
        choke_score = 0.0
        choke_drivers = []
        if whp < 0.25 * max(15.0, whp_med) and disch < 0.75 * max(1.0, disch_med) and amps > 1.10 * max(1.0, amps_med):
            choke_score = 0.95
            choke_drivers.append(("WHP (PSI)", f"{whp:.1f} PSI (Zero surface backpressure)"))
            choke_drivers.append(("VSD Amps/Load", f"{amps:.1f} A (Pump runout flow overload)"))
        scores["Open Choke"] = choke_score
        drivers["Open Choke"] = choke_drivers

        # -------------------------------------------------------------
        # 10. Undervoltage (Low voltage supply causing current surge)
        # -------------------------------------------------------------
        uv_score = 0.0
        uv_drivers = []
        if volt < 0.85 * max(100.0, volt_med) and volt > 50.0:
            uv_score += 0.65
            uv_drivers.append(("Volt", f"{volt:.1f} V (Grid sag below nominal {volt_med:.0f} V)"))
            if amps > 1.10 * max(1.0, amps_med):
                uv_score += 0.30
                uv_drivers.append(("VSD Amps/Load", f"{amps:.1f} A (Current rising to maintain kW)"))
        scores["Undervoltage"] = min(0.95, uv_score) if uv_score >= 0.60 else 0.0
        drivers["Undervoltage"] = uv_drivers

        # -------------------------------------------------------------
        # 11. Phase Imbalance (Insulation breakdown & abnormal heating)
        # -------------------------------------------------------------
        phase_score = 0.0
        phase_drivers = []
        if leak > 25.0:
            phase_score += 0.55
            phase_drivers.append(("Leak Current Ct", f"{leak:.1f} mA (Ground insulation breakdown)"))
        if m_temp > 92.0 and amps < 1.15 * max(1.0, amps_med):
            phase_score += 0.40
            phase_drivers.append(("Motor temp °C", f"{m_temp:.1f}°C (Unbalanced heating)"))
        scores["Phase Imbalance"] = min(0.95, phase_score) if phase_score >= 0.50 else 0.0
        drivers["Phase Imbalance"] = phase_drivers

        # -------------------------------------------------------------
        # 12. Motor Overload (Continuous excessive current draw)
        # -------------------------------------------------------------
        ol_score = 0.0
        ol_drivers = []
        if amps > 1.28 * max(1.0, amps_med) and vib <= 0.28:
            ol_score += 0.60
            ol_drivers.append(("VSD Amps/Load", f"{amps:.1f} A (+{int((amps/amps_med-1)*100)}% over rated)"))
            if m_temp > 88.0:
                ol_score += 0.35
                ol_drivers.append(("Motor temp °C", f"{m_temp:.1f}°C (Thermal overload)"))
        scores["Motor Overload"] = min(0.95, ol_score) if ol_score >= 0.55 else 0.0
        drivers["Motor Overload"] = ol_drivers

        # -------------------------------------------------------------
        # 13. Sensor Drift / Failure (Flatline or unrealistic reading)
        # -------------------------------------------------------------
        drift_score = 0.0
        drift_drivers = []
        if inp < 0.0 or disch < 0.0 or m_temp < -10.0 or volt < 0.0:
            drift_score = 0.95
            drift_drivers.append(("Sensor Integrity", "Negative physical measurement detected"))
        scores["Sensor Drift"] = drift_score
        drivers["Sensor Drift"] = drift_drivers

        # -------------------------------------------------------------
        # Select Primary Fault & Compute Health Score
        # -------------------------------------------------------------
        best_fault = "Normal Operation"
        best_score = 0.0
        for f_name, f_score in scores.items():
            if f_score > best_score and f_score >= 0.45:
                best_score = f_score
                best_fault = f_name

        if best_fault == "Normal Operation":
            health_score = 98.0 - (vib * 10.0) - max(0.0, (m_temp - 75.0) * 0.5)
            health_score = max(75.0, min(100.0, health_score))
            alert_level = "🟢 NORMAL"
            confidence = 0.95
            est_trip = "N/A (Stable Operation)"
            primary_drivers = [("All Sensors", "Within normal calibrated boundaries")]
        else:
            health_score = max(5.0, (1.0 - best_score) * 80.0)
            severity = FAULT_DEFINITIONS.get(best_fault, {}).get("severity", "WARNING")
            alert_level = "🔴 CRITICAL" if severity == "CRITICAL" else "🟡 WATCHLIST"
            confidence = best_score
            primary_drivers = drivers.get(best_fault, [])

            if best_score > 0.85:
                est_trip = "Immediate (< 2 Hours)"
            elif best_score > 0.65:
                est_trip = "6 to 24 Hours"
            else:
                est_trip = "24 to 48 Hours"

        fault_info = FAULT_DEFINITIONS.get(best_fault, {
            "description": "All electrical, thermal, mechanical, and hydraulic parameters within healthy baseline envelope.",
            "action": "Maintain current operating parameters; continue standard monitoring."
        })

        return {
            "primary_fault": best_fault,
            "confidence": f"{confidence * 100:.1f}%",
            "confidence_val": round(confidence, 4),
            "health_score": round(health_score, 1),
            "status": alert_level,
            "est_time_to_trip": est_trip,
            "description": fault_info["description"],
            "action_advisory": fault_info["action"],
            "root_cause_drivers": primary_drivers,
            "all_scores": {k: f"{v*100:.1f}%" for k, v in scores.items() if v > 0.20}
        }
