"""
Test Suite: Figure Factory Forensic Renderers & Anti-Hardcoding Verifications
=============================================================================
Asserts:
1. Vertical marker x-coordinate matches incident_meta['timestamp'] exactly.
2. Calibration corridor bounds dynamically differ between distinct wells (no hardcoding).
3. Evidence table calculates non-zero deviation for tripped sensors.
4. Empty and low-sample (< 5 rows) DataFrames trigger the defensive warning guard.
"""

import sys
from pathlib import Path
import pytest
import pandas as pd

# Add code directory to path
ROOT_DIR = Path(r"X:\TAS\Agentic_project")
CODE_DIR = ROOT_DIR / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from eda.figure_factory import render_incident_tipping_timeline, build_evidence_comparison_table
from models.diagnostic_engine import WellDiagnosticEngine


@pytest.fixture
def mock_telemetry_window():
    """Generates a 30-minute mock telemetry window with a realistic trip."""
    timestamps = [
        f"2026-09-03T10:{m:02d}:00Z" for m in range(0, 30)
    ]
    inp = [420.0 - (0.5 * m) if m < 15 else 80.0 for m in range(30)]
    amps = [52.0 if m < 15 else 18.0 for m in range(30)]
    disch = [1450.0 if m < 15 else 1380.0 for m in range(30)]
    temp = [68.0 if m < 15 else 85.0 + (0.5 * (m - 15)) for m in range(30)]
    vib = [0.10 if m < 15 else 0.18 for m in range(30)]
    freq = [50.0] * 30

    return pd.DataFrame({
        "Report_DateTime": timestamps,
        "Inp bar/psi": inp,
        "Disch pr. Bar/psi": disch,
        "VSD Amps/Load": amps,
        "Frequency": freq,
        "Motor temp °C": temp,
        "Vibration G's-Vx": vib
    })


def test_vertical_marker_exact_timestamp(mock_telemetry_window):
    """Assertion 1: Vertical trip line must strictly match incident_meta timestamp."""
    target_ts = "2026-09-03T10:15:00Z"
    meta = {
        "timestamp": target_ts,
        "fault": "Dry-Well Pump Off",
        "health_score": 38.0
    }
    fig = render_incident_tipping_timeline(mock_telemetry_window, meta)

    # Check shapes for vline x-coordinate
    vline_shapes = [s for s in fig.layout.shapes if s.x0 == target_ts and s.x1 == target_ts]
    assert len(vline_shapes) >= 1, f"Expected vertical marker shape at x={target_ts}, found: {[s.x0 for s in fig.layout.shapes]}"
    assert vline_shapes[0].x0 == target_ts

    # Check annotations for fault label
    matched_annos = [a for a in fig.layout.annotations if a.text and "Dry-Well Pump Off" in a.text and a.x == target_ts]
    assert len(matched_annos) >= 1, f"Expected annotation matching fault at {target_ts}"


def test_distinct_wells_different_corridors(mock_telemetry_window):
    """Assertion 2: Corridor bounds must dynamically vary based on well profile (FNW-01 vs FNW-02)."""
    eng = WellDiagnosticEngine()
    prof_01 = eng.registry.get_well_profile("FNW-01")
    prof_02 = eng.registry.get_well_profile("FNW-02")

    sensor_01_inp = prof_01.get("sensors", {}).get("Inp bar/psi", {})
    sensor_02_inp = prof_02.get("sensors", {}).get("Inp bar/psi", {})
    
    assert sensor_01_inp.get("median") != sensor_02_inp.get("median"), "Distinct wells must have distinct median baselines"
    assert sensor_01_inp.get("min") != sensor_02_inp.get("min"), "Distinct wells must have distinct corridor boundaries"


def test_evidence_table_nonzero_deviation():
    """Assertion 3: Evidence table must calculate non-zero deviations for tripped sensors."""
    eng = WellDiagnosticEngine()
    prof = eng.registry.get_well_profile("FNW-01")
    
    tripped_raw = {
        "Inp bar/psi": 50.0,
        "Disch pr. Bar/psi": 1200.0,
        "VSD Amps/Load": 15.0,
        "Motor temp °C": 98.0,
        "Vibration G's-Vx": 0.25
    }
    tbl = build_evidence_comparison_table(tripped_raw, prof)
    assert not tbl.empty, "Evidence table should not be empty"

    deviations = tbl["Deviation vs Baseline"].tolist()
    non_zero_devs = [d for d in deviations if d not in ["+0.0%", "-0.0%", "N/A"]]
    assert len(non_zero_devs) > 0, f"Expected non-zero deviations for tripped sensors, got: {deviations}"


def test_empty_and_low_sample_guard():
    """Assertion 4: Empty or < 5 rows dataframes must return the defensive warning guard."""
    meta = {"timestamp": "2026-09-03T10:15:00Z", "fault": "Test", "health_score": 90.0}

    # Case A: None
    fig_none = render_incident_tipping_timeline(None, meta)
    assert len(fig_none.layout.annotations) == 1
    assert "Insufficient" in fig_none.layout.annotations[0].text or "No telemetry" in fig_none.layout.annotations[0].text

    # Case B: < 5 rows
    df_tiny = pd.DataFrame({"Report_DateTime": ["2026-09-03T10:00:00Z"], "Inp bar/psi": [400.0]})
    fig_tiny = render_incident_tipping_timeline(df_tiny, meta)
    assert len(fig_tiny.layout.annotations) == 1
    assert "< 5 samples" in fig_tiny.layout.annotations[0].text


def test_offline_standby_suppression():
    """Assertion 5: Unpowered parked well (VFD STS=0, Amps=0) must classify as STANDBY with zero false alarms."""
    eng = WellDiagnosticEngine()
    parked_raw = {
        "VFD STS": 0.0,
        "VSD Amps/Load": 0.0,
        "Volt": 0.0,
        "Frequency": 0.0,
        "Inp bar/psi": 900.0,
        "Disch pr. Bar/psi": 903.0,
        "Motor temp °C": 80.0,
        "Vibration G's-Vx": 0.1
    }
    res = eng.evaluate_live_telemetry("FS-014", parked_raw, verbose=False)
    diag = res["diagnostic"]
    assert "STANDBY" in diag["status"], f"Expected STANDBY status, got: {diag['status']}"
    assert diag["primary_fault"] == "Well Offline / Standby"
    assert diag["confidence"] == "100.0%"
    assert "parked" in diag["description"].lower() or "standby" in diag["description"].lower()


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(["-v", __file__]))
