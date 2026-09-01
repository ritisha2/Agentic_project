"""
Forensic inspection script for Well FS-010.
Analyzes exact raw database rows, canonical translation, features,
Model 1 (Rules), Model 2 (Classifier), Model 5 (Anomaly), and Decision Fusion.
"""

import sys
import json
import asyncio
import aiosqlite
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from backend.config import DB_PATH
from backend.database import db
from backend.database_ml import ml_db
from backend.adapters.telemetry_adapter import record_to_canonical
from backend.services.unified_pipeline import esp_pipeline
from ml.data.canonical_schema import FaultClass


async def audit_fs010():
    print("=" * 70)
    print("1. INSPECTING RAW TELEMETRY ROWS FOR FS-010 IN SQLite (opg_wells.db)")
    print("=" * 70)

    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM opg_well_telemetry WHERE well_id = 'FS-010' ORDER BY timestamp DESC LIMIT 5"
        ) as cursor:
            rows = await cursor.fetchall()

        count_res = await conn.execute(
            "SELECT COUNT(*), scenario, data_category, operating_state, trip_cause, status "
            "FROM opg_well_telemetry WHERE well_id = 'FS-010' GROUP BY scenario, data_category, operating_state, trip_cause, status"
        )
        group_counts = await count_res.fetchall()

    print("Distribution of FS-010 rows in database:")
    for gc in group_counts:
        print(f"  Count: {gc[0]} | Scenario: {gc[1]} | Category: {gc[2]} | State: {gc[3]} | Trip Cause: '{gc[4]}' | Status: {gc[5]}")

    if not rows:
        print("ERROR: No rows found for FS-010!")
        return

    latest_row = dict(rows[0])
    print("\nLatest raw record for FS-010:")
    for k, v in latest_row.items():
        if k != "raw_payload":
            print(f"  {k}: {v}")

    print("\n" + "=" * 70)
    print("2. CANONICAL CONVERSION")
    print("=" * 70)
    canonical = record_to_canonical(latest_row)
    print(f"Canonical Object: {canonical}")

    print("\n" + "=" * 70)
    print("3. RUNNING COMPLETE UNIFIED PIPELINE ON FS-010")
    print("=" * 70)
    assessment = await esp_pipeline.process_telemetry(canonical, persist_db=False)
    dump = assessment.model_dump()

    print(f"Overall Status: {dump['overall_status']}")
    print(f"Rule Status (Model 1): {dump['rule_status']}")
    print(f"Fault Status (Model 2 Classifier): {dump['fault_status']} ({dump['fault_name']}) - Conf: {dump['fault_probability']:.2%}")
    print(f"Future Risk (Model 3): {dump['future_risk']}")
    print(f"RUL Status (Model 4): {dump['rul']['status']} - Reason: {dump['rul']['reason']}")
    print(f"Anomaly Score (Model 5): {dump['anomaly']['anomaly_score']:.4f} (Status: {dump['anomaly']['anomaly_status']})")
    print(f"Top Reasons: {dump['top_reasons']}")
    print(f"Operator Action: {dump['operator_action']}")
    print(f"Technical Explanation: {dump['technical_explanation']}")

    print("\n" + "=" * 70)
    print("4. PARAMETER EVALUATIONS (RULE ENVELOPE CHECKS)")
    print("=" * 70)
    for p in dump['parameter_evaluations']:
        print(f"  [{p['status']}] {p['parameter']} ({p['canonical_name']}): Val={p['value']} {p['unit']} | Ref=({p['reference_min']}..{p['reference_max']}) | Eng=({p['engineering_min']}..{p['engineering_max']}) | Msg: {p['message']}")

    print("\n" + "=" * 70)
    print("5. MODEL 2 PROBABILITIES ACROSS ALL CLASSES")
    print("=" * 70)
    features = esp_pipeline.feature_extractor.extract_features(canonical)
    if esp_pipeline.classifier.is_ready():
        probs = esp_pipeline.classifier.predict_proba(features)
        print("XGBoost/Classifier class probabilities for FS-010:")
        for cls_name, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cls_name:25s}: {prob:.4f} ({prob*100:.2f}%)")

    print("\n" + "=" * 70)
    print("6. MODEL 5 SHAP ATTRIBUTIONS / DEVIATIONS")
    print("=" * 70)
    print(json.dumps(dump['shap_contributions'], indent=2))


if __name__ == "__main__":
    asyncio.run(audit_fs010())
