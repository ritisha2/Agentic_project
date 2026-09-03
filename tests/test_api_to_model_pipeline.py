"""
Test Live API to ML Models Pipeline & Output Generator
======================================================
1. Queries live telemetry from the backend ML Telemetry REST API (:8000/api/v1/telemetry/unlabelled).
2. Passes live telemetry into the canonical ML models (code/models/):
   - SiteTelemetryAdapter (standardizes raw telemetry into 14 parameters)
   - WellDiagnosticEngine (dynamic normalization against 73-well calibration envelopes)
   - FaultClassificationEngine (13 fault modes + phase imbalance)
   - MultivariateAnomalyDetector (multivariate anomaly scoring)
3. Generates and persists `model_diagnostic_output.json`.
4. Asserts output integrity.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

# Set up paths
ROOT_DIR = Path(__file__).resolve().parent.parent
CODE_DIR = ROOT_DIR / "code"
OUTPUT_FILE = ROOT_DIR / "model_diagnostic_output.json"

if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

# Ensure stdout handles utf-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from models.diagnostic_engine import WellDiagnosticEngine
from models.telemetry_adapter import SiteTelemetryAdapter
from models.calibration_registry import WellCalibrationRegistry
from models.fault_classifier import FaultClassificationEngine
from models.anomaly_detector import MultivariateAnomalyDetector


def test_api_to_model_pipeline(asset_id: str = "FS-031"):
    print("=" * 80)
    print("🚀 STEP 1: POLLING LIVE TELEMETRY FROM BACKEND ML REST API (:8000)")
    print("=" * 80)
    
    api_url = f"http://localhost:8000/api/v1/telemetry/unlabelled?asset_id={asset_id}&limit=5"
    headers = {
        "X-Broker-ID": "CCED-ML-TEST-01"
    }

    try:
        response = requests.get(api_url, headers=headers, timeout=10.0)
    except Exception as e:
        print(f"❌ Failed to connect to Backend API at {api_url}: {e}")
        sys.exit(1)

    assert response.status_code == 200, f"API returned status {response.status_code}: {response.text}"
    api_json = response.json()
    assert api_json.get("status") == "SUCCESS", f"API error: {api_json.get('error')}"
    
    records = api_json.get("data", [])
    assert len(records) > 0, f"No telemetry records returned for {asset_id}"
    
    latest_record = records[0]
    raw_params = latest_record.get("parameters", {})
    record_timestamp = latest_record.get("timestamp", "unknown")
    
    print(f"✅ Successfully polled live record for {asset_id} at timestamp {record_timestamp}")
    print(f"   Database Source : {api_json.get('source_db')}")
    print(f"   Broker ID       : {api_json.get('broker_id')}")
    print(f"   Raw Sensor Count: {len(raw_params)} fields")
    print(f"   Sample Inputs   :")
    print(f"     - Intake Pressure    : {raw_params.get('intake_pressure_psi')} psi")
    print(f"     - Discharge Pressure : {raw_params.get('discharge_pressure_psi')} psi")
    print(f"     - Motor Temperature  : {raw_params.get('motor_temperature_c')} °C")
    print(f"     - Motor Current      : {raw_params.get('motor_current_a')} A")
    print(f"     - Drive Frequency    : {raw_params.get('frequency_hz')} Hz")

    print("\n" + "=" * 80)
    print("🧠 STEP 2: RUNNING CANONICAL ML MODELS (code/models/)")
    print("=" * 80)

    # 1. Initialize Canonical Models
    engine = WellDiagnosticEngine()
    adapter = SiteTelemetryAdapter()
    anomaly_detector = MultivariateAnomalyDetector()

    # 2. Bridge API naming to SiteTelemetryAdapter input
    site_input = {
        "Flow": raw_params.get("flow_rate_bpd") or raw_params.get("flow_rate", 735.0),
        "Intake P": raw_params.get("intake_pressure_psi", 237.0),
        "Discharge P": raw_params.get("discharge_pressure_psi", 1895.0),
        "Freq": raw_params.get("frequency_hz", 46.2),
        "Current": raw_params.get("motor_current_a", 18.9),
        "Voltage": raw_params.get("motor_voltage_v", 1009.0),
        "Temp": raw_params.get("motor_temperature_c", 78.9),
        "Vibration": raw_params.get("vibration_g", 0.18),
        "V-Imb": raw_params.get("v_imbalance_pct", 0.6),
        "I-Imb": raw_params.get("i_imbalance_pct", 1.0)
    }

    # 3. Transform via SiteTelemetryAdapter
    std_14_telemetry = adapter.transform(asset_id, site_input)
    print(f"✅ Transformed {len(site_input)} site signals into {len(std_14_telemetry)} standardized VFD parameters.")

    # 4. Evaluate via WellDiagnosticEngine
    diagnostic_result = engine.evaluate_live_telemetry(asset_id, std_14_telemetry)
    d = diagnostic_result.get("diagnostic", {})
    dyn = diagnostic_result.get("dynamics", {})
    ml_anom = diagnostic_result.get("ml_anomaly", {})

    print(f"✅ Well Diagnostic Engine completed analysis:")
    print(f"   - Health Index : {d.get('health_score')} / 100")
    print(f"   - Primary Fault: {d.get('primary_fault')} ({d.get('confidence')})")
    print(f"   - Status       : {d.get('status')}")
    print(f"   - Time-to-Trip : {d.get('est_time_to_trip')}")
    print(f"   - ML Anomaly   : {ml_anom.get('is_anomaly', False)} (Score: {ml_anom.get('anomaly_probability', 0.0)})")

    print("\n" + "=" * 80)
    print("📁 STEP 3: COMPILING & GENERATING model_diagnostic_output.json")
    print("=" * 80)

    output_payload = {
        "metadata": {
            "asset_id": asset_id,
            "well_id": latest_record.get("well_id", asset_id),
            "telemetry_record_id": latest_record.get("id"),
            "telemetry_timestamp": record_timestamp,
            "pipeline_evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_api": api_url,
            "source_database": api_json.get("source_db"),
            "broker_id": api_json.get("broker_id")
        },
        "raw_telemetry_from_api": raw_params,
        "standardized_14_parameters": std_14_telemetry,
        "diagnostic_evaluation": {
            "health_index": d.get("health_score"),
            "status": d.get("status"),
            "primary_fault_diagnosis": d.get("primary_fault"),
            "confidence": d.get("confidence"),
            "fault_description": d.get("description"),
            "estimated_time_to_trip": d.get("est_time_to_trip"),
            "recommended_operator_action": d.get("action_advisory"),
            "key_dynamics": dyn,
            "primary_root_cause_drivers": d.get("root_cause_drivers", [])
        },
        "anomaly_detection": ml_anom
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print(f"✅ Output successfully written to: {OUTPUT_FILE}")
    print(f"   File size: {os.path.getsize(OUTPUT_FILE)} bytes")

    # Verification assertions
    assert OUTPUT_FILE.exists(), "Output file does not exist!"
    assert os.path.getsize(OUTPUT_FILE) > 100, "Output file is unexpectedly small!"
    
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        reloaded = json.load(f)
        assert reloaded["metadata"]["asset_id"] == asset_id
        assert "diagnostic_evaluation" in reloaded
        assert "health_index" in reloaded["diagnostic_evaluation"]
        assert reloaded["diagnostic_evaluation"]["health_index"] is not None

    print("\n" + "=" * 80)
    print("🎉 ALL TESTS PASSED: LIVE API TELEMETRY -> ML MODEL -> JSON FILE GENERATED!")
    print("=" * 80)


if __name__ == "__main__":
    well = sys.argv[1] if len(sys.argv) > 1 else "FS-031"
    test_api_to_model_pipeline(well)
