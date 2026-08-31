"""
Query -> Response logger for backend validation.

Runs a list of queries against the real esp_agent Supervisor (NDJSON stream endpoint)
and prints/saves ONLY:
  - the query
  - the LLM/advisory response text
  - the visualization manifest JSON (VisualizationSpec) that would be sent to the
    frontend rendering layer for that response, if any was generated

No health checks, no phase banners, no internal logs — clean query/response/visual
records only, suitable for building a golden query catalogue.

Manifest shape (matches src/schemas/visualization.py:VisualizationSpec, what the
frontend actually receives to decide how/what to render):
  {
    "vis_id": "...",
    "type": "plotly_chart" | "prediction" | "pump_curve" | "scenario" | "timeline" |
             "evidence_graph" | "metric" | "table",
    "title": "...",
    "data_ref": [...],
    "evidence_ids": [...],
    "chart": {...} | null,          # only the field matching `type` is populated
    "prediction": {...} | null,
    "scenario": {...} | null,
    "pump_curve": {...} | null,
    "timeline": {...} | null,
    "evidence_graph": {...} | null,
    "metric": {...} | null,
    "table": {...} | null
  }
If no visualization was produced for a query, "visualizations" is an empty list.

Usage:
    cd X:\\TAS\\Agentic_project\\esp_agent

    # Inline queries (quick check):
    .venv\\Scripts\\python.exe query_response_logger.py --query "diagnose motor overheating" --asset FS-010

    # A batch from a JSON file: ["query 1", "query 2", ...]
    #   or [{"query": "...", "asset_id": "FS-031"}, ...]
    .venv\\Scripts\\python.exe query_response_logger.py --queries-file queries.json

    # Save the clean output as JSON for later diffing/regression:
    .venv\\Scripts\\python.exe query_response_logger.py --queries-file queries.json --out results.json
"""

import argparse
import json
import logging
import sys

import httpx

# Silence httpx's own request logging — we want ONLY query/response/visual output.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

DEFAULT_ASSET = "FS-010"


def load_queries(args):
    """Return a list of {"query": str, "asset_id": str} dicts from CLI args / file."""
    items = []
    if args.query:
        items.append({"query": args.query, "asset_id": args.asset})
    if args.queries_file:
        with open(args.queries_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for entry in data:
            if isinstance(entry, str):
                items.append({"query": entry, "asset_id": args.asset})
            elif isinstance(entry, dict):
                items.append({"query": entry["query"], "asset_id": entry.get("asset_id", args.asset)})
    if not items:
        print("No queries provided. Use --query \"...\" or --queries-file queries.json", file=sys.stderr)
        sys.exit(1)
    return items


def run_query(gateway: str, query: str, asset_id: str, timeout: float) -> dict:
    """
    Stream one query through the real Supervisor and collect:
      - response: the assembled narrative text (same text the UI renders)
      - visualizations: list of visualization_spec manifests (usually 0 or 1)
    """
    response_text_parts = []
    visualizations = []
    assessment, diagnosis, recommendation, confidence = "", "", "", None

    body = {"user_query": query, "asset_id": asset_id}
    with httpx.stream("POST", f"{gateway}/api/ui/agent/stream", json=body, timeout=timeout) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue

            etype = evt.get("type")
            if etype == "text_delta":
                response_text_parts.append(evt.get("delta", ""))
            elif etype == "advisory":
                adv = evt.get("advisory", {})
                assessment = adv.get("assessment", "")
                diagnosis = adv.get("diagnosis", "")
                recommendation = adv.get("recommendation", "")
                confidence = adv.get("confidence")
            elif etype == "generative_ui":
                spec = evt.get("visualization_spec")
                if spec:
                    visualizations.append(spec)
                elif evt.get("kind"):
                    # Fallback shape if visualization_spec wasn't attached for this event.
                    visualizations.append({
                        "vis_id": evt.get("chart_id"),
                        "type": evt.get("kind"),
                        "title": evt.get("title"),
                        "data_ref": [],
                        "evidence_ids": [],
                    })

    return {
        "query": query,
        "asset_id": asset_id,
        "response": {
            "assessment": assessment,
            "diagnosis": diagnosis,
            "recommendation": recommendation,
            "confidence": confidence,
            "narrative": "".join(response_text_parts).strip(),
        },
        "visualizations": visualizations,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gateway", default="http://127.0.0.1:8090")
    ap.add_argument("--asset", default=DEFAULT_ASSET, help="Default asset_id for queries that don't specify one")
    ap.add_argument("--query", help="A single query to run")
    ap.add_argument("--queries-file", help="Path to a JSON file: list of strings or list of {query, asset_id}")
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--out", help="Optional path to save the full result set as JSON")
    args = ap.parse_args()

    queries = load_queries(args)
    results = []

    for item in queries:
        result = run_query(args.gateway, item["query"], item["asset_id"], args.timeout)
        results.append(result)

        # Clean console output — query, response, visual manifest. Nothing else.
        print(f"Q: {result['query']}")
        resp = result["response"]
        print(f"A: {resp['narrative'] or resp['assessment']}")
        if result["visualizations"]:
            print(f"VISUALS: {json.dumps(result['visualizations'], indent=2)}")
        else:
            print("VISUALS: none")
        print("-" * 70)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Saved {len(results)} result(s) to {args.out}")


if __name__ == "__main__":
    main()
