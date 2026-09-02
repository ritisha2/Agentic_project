"""
CCED VFD Multi-Well Anomaly Detection & 13-Fault Diagnostic Engine
==================================================================
Root facade module exposing the full `models` package for seamless backward compatibility.
"""

from models import (
    WellCalibrationRegistry,
    NormalizationLayer,
    FaultClassificationEngine,
    MultivariateAnomalyDetector,
    WellDiagnosticEngine,
    FAULT_DEFINITIONS,
    STANDARD_SENSORS,
    clean_col_key
)

__all__ = [
    "WellCalibrationRegistry",
    "NormalizationLayer",
    "FaultClassificationEngine",
    "MultivariateAnomalyDetector",
    "WellDiagnosticEngine",
    "FAULT_DEFINITIONS",
    "STANDARD_SENSORS",
    "clean_col_key"
]

if __name__ == "__main__":
    from test_fault_scenarios import run_all_tests
    run_all_tests()
