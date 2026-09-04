"""
Backend Routing Assignment Verification Probe for 300 Queries
Tests each query in queries_catalogue_300.json against IntentRouter.
Outputs detailed assignment and summary metrics to routing_assignment_report_300.json.
"""

import os
import sys
import json
from pathlib import Path
from collections import defaultdict

# Configure UTF-8 for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Setup import path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.agent.intent_router import IntentRouter
from src.agent.objective_registry import ObjectiveRegistry


def main():
    catalogue_path = ROOT_DIR / "queries_catalogue_300.json"
    report_path = ROOT_DIR / "routing_assignment_report_300.json"

    with open(catalogue_path, "r", encoding="utf-8") as f:
        catalogue = json.load(f)

    registry = ObjectiveRegistry()
    router = IntentRouter(registry=registry)

    results = []
    objective_stats = defaultdict(lambda: {"total": 0, "correct": 0, "paths": defaultdict(int)})
    overall_correct = 0
    total_queries = len(catalogue)

    print(f"============================================================")
    print(f"🚀 Running Backend Routing Probe for {total_queries} Queries")
    print(f"============================================================")

    for idx, item in enumerate(catalogue, 1):
        query = item["query"]
        expected_obj = item["objective_id"]
        
        # Route query through IntentRouter
        route_result = router.route(query)
        assigned_obj, confidence, path_used, is_ambiguous = route_result

        is_match = (assigned_obj == expected_obj)
        if is_match:
            overall_correct += 1
            objective_stats[expected_obj]["correct"] += 1

        objective_stats[expected_obj]["total"] += 1
        objective_stats[expected_obj]["paths"][path_used] += 1

        results.append({
            "id": item["id"],
            "query": query,
            "expected_objective": expected_obj,
            "assigned_objective": assigned_obj,
            "confidence": round(confidence, 3),
            "path_used": path_used,
            "is_ambiguous": is_ambiguous,
            "is_match": is_match
        })

    # Save detailed report
    summary = {
        "total_queries": total_queries,
        "overall_correct": overall_correct,
        "overall_accuracy_pct": round((overall_correct / total_queries) * 100, 2),
        "objective_breakdown": {}
    }

    print("\n------------------------------------------------------------")
    print(f"{'Objective ID':<35} | {'Acc':<8} | {'Correct/Total':<13} | Top Path")
    print("------------------------------------------------------------")

    for obj_id in sorted(objective_stats.keys()):
        stats = objective_stats[obj_id]
        tot = stats["total"]
        corr = stats["correct"]
        pct = round((corr / tot) * 100, 1) if tot > 0 else 0.0
        top_p = max(stats["paths"].items(), key=lambda x: x[1])[0] if stats["paths"] else "N/A"
        
        summary["objective_breakdown"][obj_id] = {
            "total": tot,
            "correct": corr,
            "accuracy_pct": pct,
            "path_distribution": dict(stats["paths"])
        }
        print(f"{obj_id:<35} | {pct:>5.1f}%  | {corr:>2}/{tot:<2}         | {top_p}")

    print("============================================================")
    print(f"🎯 Overall Routing Accuracy: {summary['overall_accuracy_pct']}% ({overall_correct}/{total_queries})")
    print(f"============================================================")

    output_payload = {
        "summary": summary,
        "assignments": results
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print(f"\n✅ Detailed assignment report saved to: {report_path}")


if __name__ == "__main__":
    main()
