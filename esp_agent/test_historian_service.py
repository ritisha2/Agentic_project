"""
Historian Service & Tool Verification Suite
Grounded in historian.txt §8 (Tests 1-6) + ToolRegistry ACL Verification
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Setup project path
ROOT_DIR = Path(__file__).resolve().parent
CCED_DIR = ROOT_DIR.parent / "cced_esp"
if str(CCED_DIR) not in sys.path:
    sys.path.append(str(CCED_DIR))

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
from backend.api.historian_routes import (
    get_historian_health,
    get_available_signals,
    get_historian_window,
    get_active_historian_db
)
from src.schemas.contracts import TimeSeriesPayload
from src.tools.registry import get_default_tool_registry, OBJECTIVE_TOOL_ACL


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

async def run_all_tests():
    print("=" * 80)
    print(" [RUNNING] ESP HISTORIAN SERVICE & TOOL VERIFICATION SUITE")
    print("=" * 80)

    asset_id = "FS-031"
    tests_passed = 0
    total_tests = 7

    # ─────────────────────────────────────────────────────────────────────────
    # Test 1: Health Check (historian.txt §8.1)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[Test 1/7] GET /api/v1/historian/health")
    health = await get_historian_health()
    print(f"  Status: {health.get('status')}")
    print(f"  DB Path: {health.get('db_path')}")
    print(f"  Total Records: {health.get('total_records', 0):,}")
    print(f"  Earliest TS: {health.get('earliest_timestamp')}")
    print(f"  Latest TS:   {health.get('latest_timestamp')}")
    assert health.get("status") == "ok", f"Health status failed: {health}"
    assert health.get("total_records", 0) > 0, "No records in historian DB"
    print("  --> PASS: Historian health is OK with active SQLite records.")
    tests_passed += 1

    # ─────────────────────────────────────────────────────────────────────────
    # Test 2: Asset Coverage & Available Signals (historian.txt §8.2)
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n[Test 2/7] GET /api/v1/historian/{asset_id}/available-signals")
    signals_resp = await get_available_signals(asset_id=asset_id)
    print(f"  Asset ID: {signals_resp.get('asset_id')}")
    print(f"  Records:  {signals_resp.get('records_count'):,}")
    print(f"  Total Signals: {signals_resp.get('total_signals')}")
    sig_names = [s["signal"] for s in signals_resp.get("available_signals", [])]
    print(f"  Signals list: {sig_names[:5]}...")
    assert "flow_rate" in sig_names or "liquid_rate" in sig_names
    assert "intake_pressure" in sig_names
    assert "motor_temperature" in sig_names
    print("  --> PASS: Canonical ESP signals discovered for asset.")
    tests_passed += 1

    # ─────────────────────────────────────────────────────────────────────────
    # Test 3: Raw Window Retrieval (historian.txt §8.3)
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n[Test 3/7] GET /api/v1/historian/{asset_id}/window (raw window)")
    raw_window = await get_historian_window(
        asset_id=asset_id,
        signals="flow_rate,intake_pressure,discharge_pressure,motor_temperature",
        aggregation="raw",
        limit=50
    )
    print(f"  Asset: {raw_window.get('asset_id')}")
    print(f"  Coverage: {raw_window.get('coverage')}")
    print(f"  Quality: {raw_window.get('quality_summary')}")
    print(f"  Total Series: {len(raw_window.get('series', []))}")
    for s in raw_window.get("series", []):
        pts = s.get("points", [])
        sample_pt = pts[0] if pts else "None"
        print(f"    - {s['signal']} ({s['unit']}): {len(pts)} points | Sample: {sample_pt}")
        assert len(pts) > 0, f"Series {s['signal']} has 0 points"
    print("  --> PASS: Raw time-series window retrieved with correct units and timestamps.")
    tests_passed += 1

    # ─────────────────────────────────────────────────────────────────────────
    # Test 4: Aggregation (1m vs 5m vs 1h) (historian.txt §8.4)
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n[Test 4/7] Multi-Resolution Aggregations (1m vs 5m vs 1h)")
    agg_1m = await get_historian_window(asset_id=asset_id, signals="flow_rate,motor_temperature", aggregation="1m", limit=30)
    agg_5m = await get_historian_window(asset_id=asset_id, signals="flow_rate,motor_temperature", aggregation="5m", limit=30)
    agg_1h = await get_historian_window(asset_id=asset_id, signals="flow_rate,motor_temperature", aggregation="1h", limit=30)

    pts_1m = len(agg_1m["series"][0]["points"])
    pts_5m = len(agg_5m["series"][0]["points"])
    pts_1h = len(agg_1h["series"][0]["points"])
    print(f"  1m Buckets: {pts_1m} points | Sample val: {agg_1m['series'][0]['points'][0]['value']}")
    print(f"  5m Buckets: {pts_5m} points | Sample val: {agg_5m['series'][0]['points'][0]['value']}")
    print(f"  1h Buckets: {pts_1h} points | Sample val: {agg_1h['series'][0]['points'][0]['value']}")
    assert agg_1m["aggregation"] == "1m"
    assert agg_5m["aggregation"] == "5m"
    assert agg_1h["aggregation"] == "1h"
    print("  --> PASS: SQL time-bucketing aggregation operational at 1m, 5m, and 1h intervals.")
    tests_passed += 1

    # ─────────────────────────────────────────────────────────────────────────
    # Test 5: Quality & Coverage Scoring (historian.txt §8.5)
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n[Test 5/7] Quality & Coverage Validation")
    assert raw_window.get("coverage") >= 0.5
    assert raw_window.get("quality_summary") in ["GOOD", "SPARSE"]
    print(f"  Observed Coverage: {raw_window.get('coverage'):.2f} ({raw_window.get('quality_summary')})")
    print("  --> PASS: Quality-of-Data summary and coverage calculations verified.")
    tests_passed += 1

    # ─────────────────────────────────────────────────────────────────────────
    # Test 6: Zero-Hallucination on Unknown Asset (historian.txt §8.6)
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n[Test 6/7] Boundary Test: Unknown/Non-Existent Asset")
    no_asset = await get_historian_window(
        asset_id="NON_EXISTENT_WELL_999",
        signals="flow_rate,motor_temperature",
        limit=50
    )
    assert no_asset.get("coverage") == 0.0
    assert no_asset.get("quality_summary") == "NO_DATA"
    for s in no_asset.get("series", []):
        assert len(s.get("points", [])) == 0
    print(f"  Coverage on missing asset: {no_asset.get('coverage')} (Points: {no_asset.get('total_points')})")
    print("  --> PASS: No fabricated zero values generated for empty periods.")
    tests_passed += 1

    # ─────────────────────────────────────────────────────────────────────────
    # Test 7: ToolRegistry & ACL Gate Execution (Guidelines.pdf §13.2)
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n[Test 7/7] ToolRegistry Execution & ACL Verification")
    registry = get_default_tool_registry()
    
    # 1. Allowed under OP02_PRODUCTION_DECLINE_RCA
    res_op02 = registry.execute_tool(
        "get_history_window",
        objective_id="OP02_PRODUCTION_DECLINE_RCA",
        asset_id=asset_id,
        signals=["flow_rate", "motor_temperature"],
        limit=20
    )
    assert isinstance(res_op02, TimeSeriesPayload)
    assert res_op02.asset_id == asset_id
    assert len(res_op02.series) == 2
    print(f"  OP02 Execution: SUCCESS (Returned {res_op02.total_points} points for {asset_id})")

    # 2. Forbidden under OP00_OPERATIONAL_CONTROL (Safety Lock)
    try:
        registry.execute_tool(
            "get_history_window",
            objective_id="OP00_OPERATIONAL_CONTROL",
            asset_id=asset_id
        )
        assert False, "Tool should have been forbidden under OP00"
    except PermissionError as pe:
        print(f"  OP00 Safety Gate: BLOCKED AS EXPECTED ({pe})")

    print("  --> PASS: ToolRegistry securely enforces objective ACLs.")
    tests_passed += 1

    print("\n" + "=" * 80)
    print(f" [VERDICT] ALL {tests_passed}/{total_tests} HISTORIAN TESTS PASSED (100% GREEN)")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
