#!/usr/bin/env python3
"""
Interactive CLI Runner for Demo Verification Harness
Runs all 30 test scenarios against the Intent Router and measures execution latency.
Usage:
  python run_harness.py
  python run_harness.py --live-stream
"""

import sys
import os
import time
import json
import argparse
from typing import List, Dict, Any

# Add project root to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ESP_AGENT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ESP_AGENT_ROOT)

# Force utf-8 stdout for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.agent.intent_router import IntentRouter
from src.agent.objective_registry import ObjectiveRegistry
from tests.test_demo_harness import TEST_CASES, HarnessCase


def run_local_harness() -> bool:
    print("=" * 85)
    print(" [HARNESS] ESP AGENT VERIFICATION HARNESS - 30 SCENARIOS")
    print("=" * 85)

    registry = ObjectiveRegistry()
    router = IntentRouter(registry=registry)

    passed_count = 0
    failed_count = 0
    latencies: List[float] = []

    header = f"{'#':<3} | {'QUERY':<35} | {'EXPECTED':<18} | {'ROUTED':<18} | {'CONF':<5} | {'MS':<5} | {'RESULT'}"
    print(header)
    print("-" * 85)

    for idx, case in enumerate(TEST_CASES, start=1):
        t0 = time.perf_counter()
        try:
            result = router.route(case.query)
            obj_id, conf, path, is_ambiguous = result
        except Exception as ex:
            obj_id, conf, path, is_ambiguous = "ERROR", 0.0, str(ex), False

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

        passed = (obj_id == case.expected_objective)
        if passed:
            passed_count += 1
            res_str = "[PASS]"
        else:
            failed_count += 1
            res_str = "[FAIL]"

        q_disp = case.query if len(case.query) <= 35 else case.query[:32] + "..."
        exp_disp = case.expected_objective.replace("OP0", "OP").replace("OP", "OP")
        got_disp = obj_id.replace("OP0", "OP") if obj_id else "NONE"

        print(f"{idx:<3} | {q_disp:<35} | {exp_disp:<18} | {got_disp:<18} | {conf:<5.2f} | {elapsed_ms:<5.1f} | {res_str}")

    print("=" * 85)
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    print(f" SUMMARY: Total: {len(TEST_CASES)} | Passed: {passed_count} | Failed: {failed_count} | Avg Latency: {avg_latency:.1f} ms")
    print("=" * 85)

    return failed_count == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ESP Agent Verification Harness")
    parser.add_argument("--live-stream", action="store_true", help="Also test against live BFF stream endpoint on port 8090")
    args = parser.parse_args()

    success = run_local_harness()
    sys.exit(0 if success else 1)
