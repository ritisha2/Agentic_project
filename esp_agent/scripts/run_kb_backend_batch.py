"""
50-Query Knowledge Base Backend Testing & JSON Interception Suite
================================================================
Executes 50 curated Knowledge Base queries against the backend LangGraph
multi-agent pipeline (identically to agent_streamlit.py before rendering)
and saves the raw StandardAdvisoryPayload JSON structures to disk.
"""

import os
import sys
import json
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List

# Fix Windows console UTF-8 encoding
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("kb_backend_batch")

# Setup project import paths
SCRIPT_DIR = Path(__file__).resolve().parent
ESP_AGENT_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = ESP_AGENT_DIR.parent

os.environ["ADVAIT_API_URL"] = ""

for p in [str(PROJECT_ROOT), str(ESP_AGENT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import argparse
parser = argparse.ArgumentParser(description="50-Query Knowledge Base Backend Batch Runner")
parser.add_argument("--fast", action="store_true", help="Run with deterministic offline LLM mock for instant execution")
parser.add_argument("--limit", type=int, default=None, help="Limit number of queries to run")
parser.add_argument("--id", type=str, default=None, help="Run specific query by ID, e.g. KB-42")
cli_args, _ = parser.parse_known_args()

if cli_args.fast:
    os.environ["LLM_OFFLINE"] = "1"

from src.agent.supervisor.user_entry import UserEntryAdapter

DATA_DIR = ESP_AGENT_DIR / "data"
CATALOGUE_PATH = DATA_DIR / "kb_test_queries_50.json"
OUTPUT_BATCH_PATH = DATA_DIR / "kb_backend_50_results.json"
SAMPLES_DIR = DATA_DIR / "kb_backend_samples"


def slugify(text: str) -> str:
    """Create safe filename slug from query."""
    import re
    cleaned = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "_", cleaned).strip("-_")[:40]


def run_batch():
    print("=" * 80)
    print("  ESP AGENT KNOWLEDGE BASE BACKEND TESTING & RAW JSON INTERCEPTION")
    print("=" * 80)
    print(f"Loading queries from: {CATALOGUE_PATH}")

    if not CATALOGUE_PATH.exists():
        print(f"ERROR: Catalogue file not found at {CATALOGUE_PATH}")
        sys.exit(1)

    with open(CATALOGUE_PATH, "r", encoding="utf-8") as f:
        queries: List[Dict[str, Any]] = json.load(f)

    if cli_args.limit:
        queries = queries[:cli_args.limit]
    if cli_args.id:
        queries = [q for q in queries if q["id"] == cli_args.id]

    print(f"Loaded {len(queries)} test queries across 5 operational categories.")
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    adapter = UserEntryAdapter()
    results = []
    category_stats: Dict[str, Dict[str, Any]] = {}
    latencies = []
    total_citations = 0

    print("-" * 80)
    print(f"{'ID':<7} | {'Cat':<6} | {'Obj':<22} | {'Conf':<5} | {'Cits':<4} | {'Time (ms)':<9} | {'Status'}")
    print("-" * 80)

    for idx, q in enumerate(queries, 1):
        q_id = q["id"]
        category = q["category"]
        query_text = q["query"]
        target_well = q.get("target_well", "FS-031")

        if category not in category_stats:
            category_stats[category] = {"count": 0, "success": 0, "citations": 0, "latencies": []}
        category_stats[category]["count"] += 1

        req_id = f"REQ-KB-{uuid.uuid4().hex[:6]}"
        sess_id = f"sess-batch-{uuid.uuid4().hex[:6]}"

        t0 = time.time()
        try:
            # Replicates the exact backend execution call made by agent_streamlit.py:1467
            advisory = adapter.run(
                user_query=query_text,
                asset_id=target_well,
                request_id=req_id,
                session_id=sess_id
            )
            elapsed_ms = round((time.time() - t0) * 1000, 2)
            latencies.append(elapsed_ms)

            # Raw backend JSON payload before Streamlit HTML rendering
            raw_payload = advisory.model_dump() if hasattr(advisory, "model_dump") else dict(advisory)
            
            citations = [
                e.get("source_id") for e in raw_payload.get("evidence", [])
                if isinstance(e, dict) and e.get("source_id")
            ]
            num_cits = len(citations)
            total_citations += num_cits

            category_stats[category]["success"] += 1
            category_stats[category]["citations"] += num_cits
            category_stats[category]["latencies"].append(elapsed_ms)

            result_entry = {
                "test_id": q_id,
                "category": category,
                "query": query_text,
                "target_well": target_well,
                "latency_ms": elapsed_ms,
                "objective_id": advisory.objective_id,
                "confidence": advisory.confidence,
                "diagnosis": advisory.diagnosis,
                "citations_count": num_cits,
                "citations": citations,
                "has_assessment": bool(advisory.assessment),
                "has_thresholds": bool(raw_payload.get("expected_vs_actual")),
                "has_constraints": bool(raw_payload.get("constraints")),
                "has_verification": bool(raw_payload.get("verification")),
                "has_provenance": bool(raw_payload.get("provenance")),
                "raw_backend_json": raw_payload
            }
            results.append(result_entry)

            # Save individual standalone sample JSON file
            sample_filename = f"{q_id}_{slugify(query_text)}.json"
            sample_path = SAMPLES_DIR / sample_filename
            with open(sample_path, "w", encoding="utf-8") as sf:
                json.dump({
                    "metadata": {
                        "test_id": q_id,
                        "category": category,
                        "query": query_text,
                        "target_well": target_well,
                        "latency_ms": elapsed_ms,
                        "timestamp": raw_payload.get("timestamp"),
                        "raw_backend_note": "This is the exact JSON payload returned by the LangGraph Supervisor before Streamlit HTML cards rendering."
                    },
                    "backend_advisory_payload": raw_payload
                }, sf, indent=2, ensure_ascii=False)

            cat_short = category[:6]
            obj_short = advisory.objective_id[:22]
            conf_str = f"{advisory.confidence*100:.0f}%" if advisory.confidence <= 1.0 else f"{advisory.confidence}%"
            print(f"{q_id:<7} | {cat_short:<6} | {obj_short:<22} | {conf_str:<5} | {num_cits:<4} | {elapsed_ms:<9.1f} | PASS [OK]")

        except Exception as ex:
            elapsed_ms = round((time.time() - t0) * 1000, 2)
            logger.error(f"Error executing {q_id}: {ex}", exc_info=True)
            results.append({
                "test_id": q_id,
                "category": category,
                "query": query_text,
                "target_well": target_well,
                "latency_ms": elapsed_ms,
                "error": str(ex),
                "status": "FAILED"
            })
            print(f"{q_id:<7} | {category[:6]:<6} | {'ERROR':<22} | {'0%':<5} | {'0':<4} | {elapsed_ms:<9.1f} | FAIL [{ex}]")

    print("-" * 80)

    # Save consolidated batch JSON
    summary_report = {
        "benchmark_metadata": {
            "title": "ESP Agent Knowledge Base Backend Batch Execution",
            "total_queries": len(queries),
            "total_completed": len([r for r in results if "error" not in r]),
            "success_rate_pct": round((len([r for r in results if "error" not in r]) / len(queries)) * 100, 2),
            "total_citations_extracted": total_citations,
            "average_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "min_latency_ms": min(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
            "execution_mode": "Direct LangGraph Supervisor (UserEntryAdapter.run)",
            "output_samples_dir": str(SAMPLES_DIR)
        },
        "category_breakdown": {
            cat: {
                "total": stats["count"],
                "success": stats["success"],
                "total_citations": stats["citations"],
                "avg_latency_ms": round(sum(stats["latencies"]) / len(stats["latencies"]), 2) if stats["latencies"] else 0
            }
            for cat, stats in category_stats.items()
        },
        "results": results
    }

    with open(OUTPUT_BATCH_PATH, "w", encoding="utf-8") as bf:
        json.dump(summary_report, bf, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("  BACKEND EXECUTION SUMMARY & BENCHMARK METRICS")
    print("=" * 80)
    print(f"Total Queries Executed : {len(queries)}")
    print(f"Successful Runs        : {summary_report['benchmark_metadata']['total_completed']} / {len(queries)} ({summary_report['benchmark_metadata']['success_rate_pct']}%)")
    print(f"Total Citations Cited  : {total_citations}")
    print(f"Average Latency        : {summary_report['benchmark_metadata']['average_latency_ms']} ms")
    print(f"Min / Max Latency      : {summary_report['benchmark_metadata']['min_latency_ms']} ms / {summary_report['benchmark_metadata']['max_latency_ms']} ms")
    print("\nCategory Breakdown:")
    for cat, cb in summary_report["category_breakdown"].items():
        print(f"  • {cat:<42}: {cb['success']}/{cb['total']} OK | {cb['total_citations']} cits | {cb['avg_latency_ms']} ms avg")

    print("\nOutput Artifacts:")
    print(f"  [1] Consolidated Batch JSON : {OUTPUT_BATCH_PATH}")
    print(f"  [2] Individual Samples Dir  : {SAMPLES_DIR} ({len(results)} JSON files)")
    print("=" * 80)


if __name__ == "__main__":
    run_batch()
