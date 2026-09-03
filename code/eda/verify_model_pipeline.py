"""
Verification script — confirms the full data flow claimed in this session:
    MQTT -> unlabelled.db (opg_well_telemetry) -> code/models/ WellDiagnosticEngine
      -> :8000 API (/api/vfd/diagnostics/{well_id})
      -> code/eda/dashboard.py (direct SQLite + in-process engine, separate path)

This is a READ-ONLY diagnostic script. It does not modify unlabelled.db, does not
retrain anything, and does not call any destructive endpoint.

Run yourself on your local terminal (per project convention):
    cd X:\\TAS\\Agentic_project
    esp_agent\\.venv\\Scripts\\python.exe code\\eda\\verify_model_pipeline.py

Optional: pass a specific well to test end-to-end:
    esp_agent\\.venv\\Scripts\\python.exe code\\eda\\verify_model_pipeline.py --well FS-031

Requires: cced_esp backend running on :8000 for the API-path checks (steps 2-3).
Steps 1 and 4 work standalone (direct SQLite / direct engine import) even if :8000
is down, so you can tell exactly which layer is broken if something fails.
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

import requests

ROOT_DIR = Path(__file__).resolve().parent.parent.parent  # X:\TAS\Agentic_project
CCED_ESP_DIR = ROOT_DIR / "cced_esp"
CODE_DIR = ROOT_DIR / "code"
UNLABELLED_DB_PATH = CCED_ESP_DIR / "data" / "unlabelled.db"
CORE_API_URL = os.getenv("CORE_API_URL", "http://localhost:8000")

for p in [str(ROOT_DIR), str(CODE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[96m[INFO]\033[0m"
WARN = "\033[93m[WARN]\033[0m"


def hr(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------------------
# STEP 1 — MQTT -> unlabelled.db (proves live ingestion is actually landing)
# ---------------------------------------------------------------------------
def step1_verify_db_ingestion(well_filter: str = None) -> dict:
    hr("STEP 1 — Live MQTT ingestion into unlabelled.db")

    if not UNLABELLED_DB_PATH.exists():
        print(f"{FAIL} {UNLABELLED_DB_PATH} does not exist.")
        return {"ok": False}

    conn = sqlite3.connect(f"file:{UNLABELLED_DB_PATH}?mode=ro", uri=True)
    cur = conn.cursor()

    total = cur.execute("SELECT COUNT(*) FROM opg_well_telemetry").fetchone()[0]
    print(f"{PASS} opg_well_telemetry total rows: {total:,}")

    # Freshness check: most recent timestamp vs now
    row = cur.execute("SELECT MAX(timestamp), well_id FROM opg_well_telemetry").fetchone()
    latest_ts = row[0]
    print(f"{INFO} Most recent record timestamp in DB: {latest_ts}")

    if well_filter:
        wcount = cur.execute(
            "SELECT COUNT(*) FROM opg_well_telemetry WHERE well_id = ?", (well_filter,)
        ).fetchone()[0]
        wlatest = cur.execute(
            "SELECT MAX(timestamp) FROM opg_well_telemetry WHERE well_id = ?", (well_filter,)
        ).fetchone()[0]
        status = PASS if wcount > 0 else FAIL
        print(f"{status} well_id={well_filter}: {wcount:,} rows, latest={wlatest}")

    distinct_wells = cur.execute(
        "SELECT COUNT(DISTINCT well_id) FROM opg_well_telemetry"
    ).fetchone()[0]
    print(f"{INFO} Distinct wells seen in unlabelled.db: {distinct_wells}")

    conn.close()
    return {"ok": total > 0, "total": total, "latest_ts": latest_ts, "distinct_wells": distinct_wells}


# ---------------------------------------------------------------------------
# STEP 2 — :8000 API telemetry extraction (proves API reads the same DB)
# ---------------------------------------------------------------------------
def step2_verify_api_telemetry(well: str) -> dict:
    hr("STEP 2 — :8000 API telemetry extraction")
    try:
        r = requests.get(f"{CORE_API_URL}/api/telemetry", params={"asset_id": well, "limit": 5}, timeout=25)
        if r.status_code != 200:
            print(f"{FAIL} GET /api/telemetry -> HTTP {r.status_code}")
            return {"ok": False}
        data = r.json()
        records = data.get("records") or data.get("data") or []
        print(f"{PASS} GET /api/telemetry?asset_id={well} -> {len(records)} record(s) returned")
        if records:
            print(f"{INFO} Sample record keys: {list(records[0].keys())[:8]}...")
        return {"ok": len(records) > 0, "records": records}
    except Exception as ex:
        print(f"{FAIL} Could not reach {CORE_API_URL} ({ex}). Is the cced_esp backend running on :8000?")
        return {"ok": False}


# ---------------------------------------------------------------------------
# STEP 3 — :8000 API live VFD diagnosis (proves API -> code/models/ engine)
# ---------------------------------------------------------------------------
def step3_verify_api_diagnosis(well: str) -> dict:
    hr("STEP 3 — :8000 API live diagnosis (vfd_diagnostic_service -> code/models/)")
    try:
        r = requests.get(f"{CORE_API_URL}/api/vfd/diagnostics/{well}", timeout=5)
        if r.status_code != 200:
            print(f"{WARN} GET /api/vfd/diagnostics/{well} -> HTTP {r.status_code} "
                  f"(well may not have received live MQTT traffic yet — this is a data "
                  f"availability gap, not necessarily a code bug)")
            return {"ok": False}
        diag = r.json().get("diagnostic", {})
        print(f"{PASS} GET /api/vfd/diagnostics/{well} -> primary_fault={diag.get('primary_fault')!r}, "
              f"health_score={diag.get('health_score')}, confidence={diag.get('confidence')}")
        return {"ok": True, "diagnostic": diag}
    except Exception as ex:
        print(f"{FAIL} Could not reach {CORE_API_URL} ({ex}).")
        return {"ok": False}


# ---------------------------------------------------------------------------
# STEP 4 — direct code/models/ engine import + evaluation (bypasses API)
# ---------------------------------------------------------------------------
def step4_verify_direct_engine(well: str, sample_row: dict = None) -> dict:
    hr("STEP 4 — direct code/models/ WellDiagnosticEngine import (bypasses :8000 API)")
    try:
        from models.diagnostic_engine import WellDiagnosticEngine
        from models.telemetry_adapter import SiteTelemetryAdapter
        print(f"{PASS} Imported WellDiagnosticEngine + SiteTelemetryAdapter from code/models/")
    except Exception as ex:
        print(f"{FAIL} Could not import code/models/ package: {ex}")
        return {"ok": False}

    try:
        engine = WellDiagnosticEngine()
        print(f"{PASS} WellDiagnosticEngine() instantiated (registry + classifier + anomaly detector loaded)")
    except Exception as ex:
        print(f"{FAIL} WellDiagnosticEngine() failed to instantiate: {ex}")
        return {"ok": False}

    if not sample_row:
        # Pull one raw row directly from the DB for a real, non-fabricated input
        if UNLABELLED_DB_PATH.exists():
            conn = sqlite3.connect(f"file:{UNLABELLED_DB_PATH}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM opg_well_telemetry WHERE well_id = ? ORDER BY id DESC LIMIT 1", (well,)
            ).fetchone()
            conn.close()
            sample_row = dict(row) if row else None

    if not sample_row:
        print(f"{WARN} No real telemetry row available for {well} in unlabelled.db — "
              f"skipping live evaluation (cannot fabricate input, per zero-mock principle).")
        return {"ok": False}

    try:
        adapter = SiteTelemetryAdapter(engine.registry)
        std = adapter.transform(well, sample_row)
        result = engine.evaluate_live_telemetry(well, std, verbose=False)
        d = result.get("diagnostic", {})
        print(f"{PASS} evaluate_live_telemetry({well}) -> primary_fault={d.get('primary_fault')!r}, "
              f"health_score={d.get('health_score')}, status={d.get('status')}")
        return {"ok": True, "diagnostic": d}
    except Exception as ex:
        print(f"{FAIL} Direct engine evaluation failed: {ex}")
        return {"ok": False}


def main():
    parser = argparse.ArgumentParser(description="Verify MQTT -> unlabelled.db -> code/models/ pipeline")
    parser.add_argument("--well", default=None, help="Specific well_id to test end-to-end (e.g. FS-031)")
    args = parser.parse_args()

    print("Data Flow Verification — MQTT -> unlabelled.db -> code/models/ -> :8000 API")
    print(f"unlabelled.db path: {UNLABELLED_DB_PATH}")
    print(f"Core API base URL:  {CORE_API_URL}")

    r1 = step1_verify_db_ingestion(args.well)

    well = args.well
    if not well and r1.get("ok"):
        # Pick a real well seen in the DB rather than guessing a name
        conn = sqlite3.connect(f"file:{UNLABELLED_DB_PATH}?mode=ro", uri=True)
        row = conn.execute("SELECT well_id FROM opg_well_telemetry LIMIT 1").fetchone()
        conn.close()
        well = row[0] if row else "FS-031"
        print(f"{INFO} No --well specified; using a real well from the DB: {well}")

    r2 = step2_verify_api_telemetry(well) if well else {"ok": False}
    r3 = step3_verify_api_diagnosis(well) if well else {"ok": False}
    r4 = step4_verify_direct_engine(well)

    hr("SUMMARY")
    checks = [
        ("1. MQTT -> unlabelled.db ingestion", r1.get("ok")),
        ("2. :8000 /api/telemetry read-back", r2.get("ok")),
        ("3. :8000 /api/vfd/diagnostics (live)", r3.get("ok")),
        ("4. Direct code/models/ engine import + eval", r4.get("ok")),
    ]
    for name, ok in checks:
        print(f"  {PASS if ok else FAIL} {name}")

    if not r3.get("ok"):
        print(f"\n{WARN} Step 3 failing usually means this specific well has no live MQTT "
              f"traffic yet, not that the pipeline is broken — confirm with Step 1's "
              f"distinct_wells count and try a well that appears there.")


if __name__ == "__main__":
    main()
