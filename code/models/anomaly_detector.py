"""
Multivariate Machine Learning Anomaly Detector Component
========================================================
Unsupervised machine learning model using Isolation Forest to detect multivariate
outliers and unknown anomalous operating vectors across the 13 normalized sensor dimensions.

Why per-well models
-------------------
Telemetry is min-max normalized against EACH well's own historical envelope
(see normalization_layer.py), so the same normalized vector can mean very different
physical states for different wells. Pooling all wells into one global Isolation Forest
therefore produces a diffuse, multimodal cloud in which some wells' perfectly-normal
operating centres sit in globally sparse regions and get misflagged as outliers.

The detector fits ONE Isolation Forest per well against that well's own reconstructed
baseline cloud, plus a single global model as a fallback for wells with no registry
profile. A well's live reading is then scored against its own baseline — the physically
meaningful comparison — so genuine normal operation reads as an inlier and only real
deviations from that well's baseline are flagged.

Calibration policy
------------------
The detector MUST be calibrated on real baseline data before it can score. Paths:

  1. fit(matrix)              -> fit the global model on an offline batch of normalized vectors.
  2. fit_from_registry(reg)   -> reconstruct realistic baseline clouds from the well
                                 calibration registry's historical per-sensor statistics
                                 and fit per-well models (+ a global fallback).

If the detector was never calibrated, score_sample() returns an explicit
"calibrated": False result with null score/flag rather than fabricating a number.
Previously the model silently self-fitted on synthetic gaussian noise centred at 0.5,
which did not match the real normalized feature space and caused nearly every genuine
reading to be flagged as a ~90% outlier.
"""

import re
from typing import Dict, List, Optional, Any
import numpy as np
from sklearn.ensemble import IsolationForest

from .calibration_registry import STANDARD_SENSORS


def _new_forest(contamination: float, random_state: int) -> IsolationForest:
    return IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )


class MultivariateAnomalyDetector:
    """
    Unsupervised ML Anomaly Detector:
    Fits Isolation Forest hyperplanes on normalized [0, 1] telemetry features
    (per-well, with a global fallback) to flag multi-sensor correlation breakdowns.
    """

    def __init__(self, contamination: float = 0.02, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        # Global fallback model (used for wells with no registry / family profile).
        self.model = _new_forest(contamination, random_state)
        # Per-well and per-family models keyed by upper-cased id. Resolution at score
        # time mirrors WellCalibrationRegistry.get_well_profile(): well -> family -> global,
        # so the baseline a reading is scored against uses the SAME sensor envelope that
        # normalize_live_telemetry() used to produce that reading.
        self._well_models: Dict[str, IsolationForest] = {}
        self._family_models: Dict[str, IsolationForest] = {}
        self.is_fitted = False
        # Provenance so consumers can tell HOW the detector was calibrated.
        self.calibration_source: Optional[str] = None
        self.n_baseline_samples: int = 0

    # ------------------------------------------------------------------ fitting
    def fit(self, normalized_feature_matrix: np.ndarray, source: str = "offline_batch"):
        """Fit the GLOBAL fallback model on a batch of normalized [0, 1] vectors."""
        if normalized_feature_matrix.ndim == 1:
            normalized_feature_matrix = normalized_feature_matrix.reshape(1, -1)
        self.model.fit(normalized_feature_matrix)
        self.is_fitted = True
        self.calibration_source = source
        self.n_baseline_samples = int(normalized_feature_matrix.shape[0])
        return self

    def _sample_baseline(self, sensors: Dict[str, Any], n: int, rng) -> List[List[float]]:
        """
        Reconstruct `n` realistic normal normalized vectors from a sensor-stats profile
        (well, family, or global). Draws N(median, std) clipped to [min, max] and min-max
        normalizes with that profile's envelope — the exact [0, 1] space live vectors occupy.
        """
        rows: List[List[float]] = []
        for _ in range(n):
            vec: List[float] = []
            for sensor in STANDARD_SENSORS:
                st = sensors.get(sensor)
                if st and st.get("max", 0.0) > st.get("min", 0.0):
                    s_min = float(st["min"])
                    s_max = float(st["max"])
                    median = float(st.get("median", (s_min + s_max) / 2.0))
                    std = float(st.get("std", 0.0))
                    if not np.isfinite(std) or std <= 0.0:
                        p10 = float(st.get("p10", s_min))
                        p90 = float(st.get("p90", s_max))
                        std = max((p90 - p10) / 2.563, (s_max - s_min) * 0.05, 1e-6)
                    val = float(rng.normal(median, std))
                    val = min(max(val, s_min), s_max)
                    norm_v = (val - s_min) / (s_max - s_min)
                else:
                    # No usable envelope -> matches the live normalization fallback of 0.5.
                    norm_v = 0.5
                vec.append(float(np.clip(norm_v, 0.0, 1.0)))
            rows.append(vec)
        return rows

    def fit_from_registry(self, registry: Any, samples_per_well: int = 200) -> bool:
        """
        Calibrate per-well AND per-family Isolation Forests (+ a global fallback) from the
        well calibration registry's historical statistics.

        Per-family models matter because live well IDs often don't match a registry key
        exactly (e.g. live 'FS-031' vs registry 'FS-31'); in that case the normalizer falls
        back to the family profile, so the anomaly baseline must resolve to the family model
        too — otherwise the reading is scored in a different normalized space than it was
        produced in.

        Returns True if at least one model was calibrated, False if no usable baseline stats
        were found (detector stays uncalibrated and score_sample() reports so honestly).

        Note: samples are drawn per-sensor independently, so each model learns per-dimension
        density rather than cross-sensor correlation structure — a deliberate, documented
        limitation, still far more faithful than a fixed 0.5-centred blob.
        """
        wells = getattr(registry, "registry", None)
        if not isinstance(wells, dict) or not wells:
            return False

        rng = np.random.default_rng(self.random_state)
        all_rows: List[List[float]] = []
        well_models: Dict[str, IsolationForest] = {}
        family_models: Dict[str, IsolationForest] = {}

        def _fit_profile(sensors: Dict[str, Any]) -> Optional[IsolationForest]:
            if not sensors:
                return None
            rows = self._sample_baseline(sensors, samples_per_well, rng)
            if not rows:
                return None
            all_rows.extend(rows)
            try:
                m = _new_forest(self.contamination, self.random_state)
                m.fit(np.asarray(rows, dtype=float))
                return m
            except Exception:
                return None

        # Per-well models.
        for well_id, wprof in wells.items():
            sensors = wprof.get("sensors", {}) if isinstance(wprof, dict) else {}
            m = _fit_profile(sensors)
            if m is not None:
                well_models[str(well_id).upper()] = m

        # Per-family models (mirror get_well_profile's family fallback).
        family_profiles = getattr(registry, "family_profiles", {}) or {}
        for fam, fprof in family_profiles.items():
            sensors = fprof.get("sensors", {}) if isinstance(fprof, dict) else {}
            m = _fit_profile(sensors)
            if m is not None:
                family_models[str(fam).upper()] = m

        if not all_rows:
            return False

        # Global fallback: prefer the registry's global profile, else the pooled cloud.
        global_profile = getattr(registry, "global_profile", {}) or {}
        global_sensors = global_profile.get("sensors", {}) if isinstance(global_profile, dict) else {}
        global_rows = self._sample_baseline(global_sensors, samples_per_well, rng) if global_sensors else []
        if global_rows:
            self.fit(np.asarray(global_rows, dtype=float), source="calibration_registry")
        else:
            self.fit(np.asarray(all_rows, dtype=float), source="calibration_registry")

        self._well_models = well_models
        self._family_models = family_models
        return True

    @staticmethod
    def _family_of(well_id: str) -> str:
        """Leading alphabetic prefix of a well id (mirrors registry family derivation)."""
        m = re.match(r"^([A-Za-z]+)", str(well_id).strip())
        return m.group(1).upper() if m else "OTHER"

    # ------------------------------------------------------------------ scoring
    def _uncalibrated_result(self) -> Dict[str, Any]:
        """Honest response when the detector has no real baseline to score against."""
        return {
            "is_anomaly": None,
            "raw_decision_score": None,
            "anomaly_probability": None,
            "calibrated": False,
            "note": (
                "Anomaly detector not calibrated on baseline data; score unavailable. "
                "Call fit()/fit_from_registry() before scoring."
            ),
        }

    def score_sample(self, norm_vector: List[float], well_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Compute anomaly score and outlier flag for a single normalized [0, 1] vector.

        Scores against the well's OWN baseline model when available, otherwise the global
        fallback. If the detector was never calibrated, returns an explicit uncalibrated
        result (null score/flag) instead of fabricating a number.
        """
        if not self.is_fitted:
            return self._uncalibrated_result()

        # Resolve the scoring model the SAME way the normalizer resolved the profile:
        # exact well -> family -> global. This guarantees the reading is scored in the
        # same normalized space it was produced in.
        model = None
        scope = "fleet_global"
        if well_id is not None:
            wid = str(well_id).upper()
            model = self._well_models.get(wid)
            if model is not None:
                scope = "per_well"
            else:
                fam_model = self._family_models.get(self._family_of(wid))
                if fam_model is not None:
                    model = fam_model
                    scope = "family"
        if model is None:
            model = self.model

        X = np.array(norm_vector, dtype=float).reshape(1, -1)
        raw_score = float(model.decision_function(X)[0])
        is_outlier = bool(model.predict(X)[0] == -1)

        # Map the signed decision score into [0.0 (normal), 1.0 (severe anomaly)].
        anomaly_prob = float(np.clip(1.0 / (1.0 + np.exp(raw_score * 10.0)), 0.0, 1.0))

        return {
            "is_anomaly": is_outlier,
            "raw_decision_score": round(raw_score, 4),
            "anomaly_probability": round(anomaly_prob, 4),
            "calibrated": True,
            "model_scope": scope,
            "calibration_source": self.calibration_source,
            "n_baseline_samples": self.n_baseline_samples,
        }
