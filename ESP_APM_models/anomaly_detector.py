"""
Multivariate Machine Learning Anomaly Detector Component
========================================================
Unsupervised machine learning model using Isolation Forest to detect multivariate
outliers and unknown anomalous operating vectors across the 13 normalized sensor dimensions.
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from sklearn.ensemble import IsolationForest


class MultivariateAnomalyDetector:
    """
    Unsupervised ML Anomaly Detector:
    Fits an Isolation Forest hyperplane on normalized [0, 1] telemetry features
    to flag multi-sensor correlation breakdowns.
    """

    def __init__(self, contamination: float = 0.02, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.model = IsolationForest(
            n_estimators=100,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1
        )
        self.is_fitted = False

    def fit(self, normalized_feature_matrix: np.ndarray):
        """Fits the Isolation Forest on a batch of normalized [0, 1] vectors."""
        if normalized_feature_matrix.ndim == 1:
            normalized_feature_matrix = normalized_feature_matrix.reshape(1, -1)
        self.model.fit(normalized_feature_matrix)
        self.is_fitted = True
        return self

    def score_sample(self, norm_vector: List[float]) -> Dict[str, Any]:
        """
        Computes anomaly score and outlier flag for a single normalized [0, 1] vector.
        """
        X = np.array(norm_vector).reshape(1, -1)
        if not self.is_fitted:
            # Synthetic fit on nominal center if model not yet fitted on offline batch
            synthetic_norm = np.clip(np.random.normal(0.5, 0.15, size=(500, len(norm_vector))), 0.0, 1.0)
            self.model.fit(synthetic_norm)
            self.is_fitted = True

        raw_score = float(self.model.decision_function(X)[0])
        is_outlier = bool(self.model.predict(X)[0] == -1)

        # Normalize score into [0.0 (normal), 1.0 (severe anomaly)]
        anomaly_prob = float(np.clip(1.0 / (1.0 + np.exp(raw_score * 10.0)), 0.0, 1.0))

        return {
            "is_anomaly": is_outlier,
            "raw_decision_score": round(raw_score, 4),
            "anomaly_probability": round(anomaly_prob, 4)
        }
