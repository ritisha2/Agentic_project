"""
ESP APM Platform — Structured Query Test Suite & Response Logger
================================================================
Executes test queries from queries_catalogue.json (3 queries per objective domain OP00–OP13)
and logs clean advisory responses, visual manifests, evidence deep-links, and routing confidence.

Modes:
  1. Direct In-Process Mode (Default & Fast): Runs queries directly against LangGraph UserEntryAdapter.
  2. REST Stream Mode (--stream): Sends queries to the live gateway at http://127.0.0.1:8090/api/ui/agent/stream.

Usage:
  # Run the full 3-queries-per-objective catalogue (42 queries) directly:
  .venv\\Scripts\\python.exe query_response_logger.py --queries-file queries_catalogue.json --out results_catalogue.json

  # Run a single domain (e.g. OP02 or OP08):
  .venv\\Scripts\\python.exe query_response_logger.py --objective OP02

  # Run a single query:
  .venv\\Scripts\\python.exe query_response_logger.py --query "Why did production drop on FS-031?" --asset FS-031
"""

import sys
import os
import time
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import os
ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
CCED_DIR = ROOT_DIR.parent / "cced_esp"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(CCED_DIR) not in sys.path:
    sys.path.append(str(CCED_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Suppress verbose internal framework logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("src").setLevel(logging.WARNING)

from src.agent.intent_router import IntentRouter
from src.agent.objective_registry import ObjectiveRegistry
from src.agent.supervisor.user_entry import UserEntryAdapter

DEFAULT_GATEWAY = "http://127.0.0.1:8090"
DEFAULT_CATALOGUE = ROOT_DIR / "queries_catalogue.json"


def run_in_process_query(query: str, asset_id: str, expected_obj: Optional[str] = None, routing_only: bool = False) -> Dict[str, Any]:
    """Run query directly against IntentRouter (and optionally UserEntryAdapter)."""
    t0 = time.monotonic()
    
    # 1. Routing
    registry = ObjectiveRegistry()
    router = IntentRouter(registry=registry)
    routed_obj, confidence, route_path = router.route(query)
    
    # 2. Execution (if not routing_only)
    assessment = ""
    recommendations = []
    status = "SUCCESS"
    if not routing_only:
        try:
            entry = UserEntryAdapter()
            advisory = entry.run(user_query=query, asset_id=asset_id)
            assessment = advisory.assessment if hasattr(advisory, "assessment") else str(advisory)
            recommendations = advisory.recommended_actions if hasattr(advisory, "recommended_actions") else []
            conf_val = getattr(advisory, "confidence_score", confidence)
        except Exception as ex:
            assessment = f"[Error executing advisory: {ex}]"
            conf_val = confidence
            status = "ERROR"
    else:
        assessment = f"Intent routed to {routed_obj} via {route_path}"
        conf_val = confidence

    latency_ms = (time.monotonic() - t0) * 1000
    match_expected = (routed_obj == expected_obj) if expected_obj else True

    return {
        "query": query,
        "asset_id": asset_id,
        "expected_objective": expected_obj,
        "routed_objective": routed_obj,
        "confidence": round(float(conf_val or confidence), 2),
        "route_path": route_path,
        "routing_match": match_expected,
        "latency_ms": round(latency_ms, 1),
        "status": status,
        "response": {
            "assessment": assessment,
            "recommendations": recommendations,
        }
    }


def run_stream_query(gateway: str, query: str, asset_id: str, timeout: float = 120.0) -> Dict[str, Any]:
    """Send query to the live REST streaming endpoint."""
    import httpx
    t0 = time.monotonic()
    response_text_parts = []
    visualizations = []
    assessment = ""
    routed_obj = "UNKNOWN"
    confidence = 0.0

    body = {"user_query": query, "asset_id": asset_id}
    try:
        with httpx.stream("POST", f"{gateway}/api/ui/agent/stream", json=body, timeout=timeout) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                except Exception:
                    continue
                
                etype = evt.get("type")
                if etype == "text_delta":
                    response_text_parts.append(evt.get("delta", ""))
                elif etype == "advisory":
                    adv = evt.get("advisory", {})
                    assessment = adv.get("assessment", "")
                    routed_obj = evt.get("objective_id", routed_obj)
                    confidence = adv.get("confidence", 0.0)
                elif etype == "generative_ui":
                    spec = evt.get("visualization_spec")
                    if spec:
                        visualizations.append(spec)
        status = "SUCCESS"
    except Exception as ex:
        assessment = f"[Stream request failed: {ex}]"
        status = "ERROR"

    latency_ms = (time.monotonic() - t0) * 1000

    return {
        "query": query,
        "asset_id": asset_id,
        "routed_objective": routed_obj,
        "confidence": confidence,
        "latency_ms": round(latency_ms, 1),
        "status": status,
        "response": {
            "assessment": assessment or "".join(response_text_parts).strip(),
        },
        "visualizations": visualizations,
    }


def main():
    ap = argparse.ArgumentParser(description="ESP APM Test Query Suite & Response Logger")
    ap.add_argument("--queries-file", "-f", default=str(DEFAULT_CATALOGUE), help="Path to queries_catalogue.json")
    ap.add_argument("--query", "-q", help="Run a single ad-hoc query")
    ap.add_argument("--asset", "-a", default="FS-031", help="Target asset ID")
    ap.add_argument("--objective", "-o", help="Filter queries by objective domain (e.g. OP02, OP08)")
    ap.add_argument("--routing-only", "-r", action="store_true", help="Validate intent routing & objective mapping only (fast, <1s for all 42 queries)")
    ap.add_argument("--stream", action="store_true", help="Send queries via HTTP REST stream (:8090) instead of direct")
    ap.add_argument("--gateway", default=DEFAULT_GATEWAY, help="Gateway URL for stream mode")
    ap.add_argument("--out", help="Save full test output to JSON file")
    args = ap.parse_args()

    # Load queries
    if args.query:
        query_items = [{"query": args.query, "asset_id": args.asset, "objective_id": args.objective}]
    else:
        qpath = Path(args.queries_file)
        if not qpath.exists():
            print(f"[-] Queries file not found: {qpath}")
            sys.exit(1)
        with open(qpath, "r", encoding="utf-8") as f:
            query_items = json.load(f)

    if args.objective:
        query_items = [q for q in query_items if args.objective.upper() in q.get("objective_id", "").upper()]

    SEP = "=" * 84
    sep = "-" * 84
    print(SEP)
    print(f" ESP APM QUERY TEST SUITE — {len(query_items)} Queries Across Objectives OP00–OP13")
    print(f" Execution Mode: {'HTTP REST Stream (:8090)' if args.stream else ('Direct Routing Validation (<1s)' if args.routing_only else 'Direct In-Process LLM Pipeline')}")
    print(SEP)

    results = []
    passed_routes = 0
    current_domain = ""

    for idx, item in enumerate(query_items, 1):
        q = item.get("query")
        asset = item.get("asset_id", args.asset)
        exp_obj = item.get("objective_id")
        domain = item.get("domain", "")

        if domain and domain != current_domain:
            current_domain = domain
            print(f"\n📁 [{exp_obj}] {domain}")
            print(f" {'-'*78}")

        if args.stream:
            res = run_stream_query(args.gateway, q, asset)
            res["expected_objective"] = exp_obj
            res["domain"] = domain
            res["routing_match"] = (res.get("routed_objective") == exp_obj) if exp_obj else True
        else:
            res = run_in_process_query(q, asset, exp_obj, routing_only=args.routing_only)
            res["domain"] = domain

        results.append(res)

        # Print clean test result line
        match_icon = "✅" if res.get("routing_match", True) else "⚠️ "
        if res.get("routing_match", True):
            passed_routes += 1

        print(f"  {match_icon} [{idx:02d}/{len(query_items):02d}] Query : \"{q}\"")
        print(f"      Asset : {asset:<12} | Route: {res.get('routed_objective')} (conf={res.get('confidence')}) | Latency: {res['latency_ms']}ms")
        resp_text = res["response"].get("assessment", "")
        if resp_text:
            print(f"      Resp  : {resp_text[:120]}…")

    print("\n" + SEP)
    accuracy = (passed_routes / len(query_items) * 100) if query_items else 0
    print(f" TEST SUITE COMPLETE: {passed_routes}/{len(query_items)} Objectives Matched ({accuracy:.1f}%)")
    print(SEP)

    if args.out:
        out_path = Path(args.out)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"[+] Full test results saved to: {out_path.resolve()}\n")


if __name__ == "__main__":
    main()
