"""
ESP APM Platform — Master End-to-End Query Execution Pipeline
=============================================================
Executes queries from routing -> multi-source evidence collection -> live LLM advisory ->
Generative UI visualization specs -> full structured JSON export.

Pipeline Stages per Query:
  1. Intent Routing        : IntentRouter (Path A / B / C) -> Objective ID & Confidence
  2. Context & Telemetry   : Asset Registry + SQLite Historian (633k pts) / Live Telemetry
  3. Statistical Analysis  : Signal slopes, inflection points, min/max, % change, sparklines
  4. Evidence Pack         : Multi-source Level A–E EvidenceItems with Real Source Deep-Links
  5. Deterministic Physics : Engineering calculations (TDH, Delta_P, BEP deviation)
  6. LLM Reasoning         : CompactContextBuilder -> Live Local Qwen2.5 LLM -> Structured Advisory
  7. Visual Manifest       : Generative UI VisualizationSpec (Plotly timeseries/curve/prediction)
  8. JSON Persistence      : Full structured JSON export with timestamps, citations, and latencies

Usage:
  # Run all queries from queries_catalogue.json:
  .venv\\Scripts\\python.exe run_full_query_pipeline.py

  # Run a specific objective domain (e.g. OP02 or OP08):
  .venv\\Scripts\\python.exe run_full_query_pipeline.py --objective OP02

  # Run first N queries:
  .venv\\Scripts\\python.exe run_full_query_pipeline.py --limit 3

  # Run a single custom query:
  .venv\\Scripts\\python.exe run_full_query_pipeline.py -q "Why did production drop on FS-031 in the last 6 hours?" -a FS-031
"""

import sys
import os
import time
import json
import uuid
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Ensure esp_agent root is strictly first so `src.*` resolves to esp_agent/src
ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
CCED_DIR = ROOT_DIR.parent / "cced_esp"
sys.path = [p for p in sys.path if p != str(ROOT_DIR) and p != str(CCED_DIR)]
sys.path.insert(0, str(ROOT_DIR))
sys.path.append(str(CCED_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Suppress internal library chatter for clean output
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("src").setLevel(logging.WARNING)

from src.agent.intent_router import IntentRouter
from src.agent.objective_registry import ObjectiveRegistry
from src.adapters.asset_service import AssetService
from src.adapters.graph import GraphAdapter
from src.tools.fetch_telemetry import get_history_window_tool
from src.services.evidence.collector import EvidenceCollector
from src.llm.context_builder import CompactContextBuilder
from src.llm.adapter import LLMAdapter
from src.llm.structured_output import AdvisoryOutputSchema, HypothesisSchema
from src.schemas.evidence import EvidenceItem

# Advisory-only safety lock: these objectives must NEVER be sent to the LLM for a
# free-form advisory. Direct actuation commands (start/stop/change frequency) are
# refused deterministically here, mirroring the production Supervisor graph's
# fail-closed `route_after_resolve_objective` -> control_refusal gate. Without this,
# a small local model can (and did) emit unsafe output like "Turn off the ESP
# immediately" for an operational-control query.
HARD_REFUSAL_OBJECTIVES = {"OP00_OPERATIONAL_CONTROL", "OBJ_OPERATIONAL_CONTROL"}


def _build_control_refusal_advisory(query: str, asset_id: str) -> AdvisoryOutputSchema:
    """Deterministic advisory-only refusal for operational-control commands (OP00)."""
    return AdvisoryOutputSchema(
        assessment=(
            f"Agent Jane is locked in Advisory-Only mode under the Safety Policy and cannot "
            f"autonomously execute direct actuation commands (start, stop, or change frequency) "
            f"on asset {asset_id}. The request '{query}' is acknowledged but will not be actioned automatically."
        ),
        hypotheses=[],
        uncertainties=[],
        recommendation=(
            "Route this control action to the authorized Control Room Operator (CRO) or execute it "
            "through the approved SCADA interface after obtaining supervisor authorization."
        ),
        verification="Confirm authorization with the lead operations supervisor before any manual SCADA adjustment.",
    )


def _extract_recommendation(advisory: Any) -> str:
    """Safely extract a recommendation string from any advisory-like object."""
    rec = getattr(advisory, "recommendation", None)
    if isinstance(rec, str) and rec.strip():
        return rec
    actions = getattr(advisory, "recommended_actions", None)
    if actions:
        first = actions[0]
        return getattr(first, "action", str(first))
    return "Monitor telemetry closely and re-evaluate at the next surveillance interval."


def _extract_verification_steps(advisory: Any) -> List[str]:
    """Normalize the advisory verification field into a clean list of steps."""
    verification = getattr(advisory, "verification", None)
    if verification is None:
        verification = getattr(advisory, "verification_plan", None)
    if isinstance(verification, str):
        # Split a single sentence-string into discrete steps on sentence boundaries.
        parts = [p.strip() for p in verification.split(".") if p.strip()]
        return parts or [verification.strip()]
    if isinstance(verification, list):
        return [str(v).strip() for v in verification if str(v).strip()]
    return []


# ═══════════════════════════════════════════════════════════════════════════
# Feature Engine & Sparklines
# ═══════════════════════════════════════════════════════════════════════════
def render_sparkline(values: List[float], width: int = 20) -> str:
    if not values:
        return ""
    bars = " ▂▃▄▅▆▇█"
    sampled = values if len(values) <= width else [
        values[int(i * (len(values) - 1) / (width - 1))] for i in range(width)
    ]
    mn, mx = min(sampled), max(sampled)
    if mx == mn:
        return bars[3] * len(sampled)
    return "".join(bars[min(int((v - mn) / (mx - mn) * (len(bars) - 1)), len(bars) - 1)] for v in sampled)


def compute_signal_features(signal_name: str, points: list, unit: str = "") -> Dict[str, Any]:
    if not points:
        return {"signal": signal_name, "n_points": 0, "unit": unit}
    vals = [p.value for p in points]
    first_v, last_v = vals[0], vals[-1]
    delta = last_v - first_v
    pct_chg = ((last_v - first_v) / abs(first_v) * 100.0) if abs(first_v) > 1e-6 else 0.0
    mean_v = sum(vals) / len(vals)
    variance = sum((v - mean_v) ** 2 for v in vals) / len(vals)
    std_v = variance ** 0.5
    slope = (last_v - first_v) / max(len(vals) - 1, 1)

    # Inflection detection
    inflection_at = None
    if len(vals) >= 10:
        half = len(vals) // 2
        s1 = (vals[half] - vals[0]) / half
        s2 = (vals[-1] - vals[half]) / max(len(vals) - 1 - half, 1)
        if (s1 * s2 < 0 and abs(s1 - s2) > 0.01) or (abs(s2) > abs(s1) * 3 and abs(s2) > 0.05):
            inflection_at = points[half].timestamp

    return {
        "signal": signal_name,
        "n_points": len(vals),
        "first": round(first_v, 2),
        "last": round(last_v, 2),
        "delta": round(delta, 2),
        "pct_change": round(pct_chg, 1),
        "mean": round(mean_v, 2),
        "std": round(std_v, 3),
        "min": round(min(vals), 2),
        "max": round(max(vals), 2),
        "slope_per_sample": round(slope, 4),
        "first_ts": points[0].timestamp,
        "last_ts": points[-1].timestamp,
        "inflection_at": inflection_at,
        "sparkline": render_sparkline(vals),
        "unit": unit,
        "quality": "GOOD" if len(vals) >= 10 else "LIMITED"
    }


def build_visualization_spec(asset_id: str, obj_id: str, features: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    """Construct Generative UI VisualizationSpec matching frontend renderer."""
    vis_id = f"VIS-{asset_id}-{uuid.uuid4().hex[:6]}"
    
    if "DECLINE" in obj_id or "STATUS" in obj_id or "EARLY" in obj_id:
        series = []
        for f in features:
            if f.get("n_points", 0) > 0:
                series.append({
                    "name": f["signal"],
                    "unit": f["unit"],
                    "first": f["first"],
                    "last": f["last"],
                    "mean": f["mean"],
                    "delta": f["delta"],
                    "pct_change": f["pct_change"]
                })
        return {
            "vis_id": vis_id,
            "type": "plotly_chart",
            "title": f"Telemetry & Trend Analysis — {asset_id}",
            "data_ref": [f["signal"] for f in features if f.get("n_points", 0) > 0],
            "evidence_ids": [f"EVID-HIST-{asset_id}-{f['signal'].upper()}" for f in features if f.get("n_points", 0) > 0],
            "chart": {
                "chart_type": "multiaxis_timeseries",
                "asset_id": asset_id,
                "series_summary": series,
            }
        }
    elif "FLEET" in obj_id:
        return {
            "vis_id": vis_id,
            "type": "table",
            "title": f"Fleet Multi-Asset Analysis Matrix",
            "data_ref": ["fleet_registry", "fleet_summary_metrics"],
            "evidence_ids": [],
            "table": {
                "scope": "FLEET",
                "focus": obj_id
            }
        }
    else:
        return {
            "vis_id": vis_id,
            "type": "evidence_graph",
            "title": f"Causal Diagnostics Graph — {asset_id}",
            "data_ref": ["esp_graph.json", "neo4j"],
            "evidence_ids": [],
            "evidence_graph": {
                "asset_id": asset_id,
                "root_symptom": query
            }
        }


# ═══════════════════════════════════════════════════════════════════════════
# End-to-End Query Execution
# ═══════════════════════════════════════════════════════════════════════════
def execute_query_pipeline(query_item: Dict[str, Any], router: IntentRouter, asset_svc: AssetService, llm_adapter: LLMAdapter) -> Dict[str, Any]:
    query = query_item.get("query", "")
    asset_id = query_item.get("asset_id", "FS-031")
    exp_obj = query_item.get("objective_id")
    domain = query_item.get("domain", "")
    t0 = time.monotonic()

    # 1. Routing
    routed_obj, route_conf, route_path = router.route(query)
    is_fleet = "FLEET" in routed_obj or asset_id == "FLEET" or "," in asset_id

    # 2. Asset & Equipment Context
    primary_asset = asset_id.split(",")[0].strip() if "," in asset_id else asset_id
    if primary_asset != "FLEET":
        try:
            asset_ctx = asset_svc.get_asset(primary_asset)
        except Exception:
            asset_ctx = None
    else:
        asset_ctx = None

    # 3. Telemetry / Historian Retrieval
    target_signals = ["flow_rate", "intake_pressure", "discharge_pressure", "motor_temperature", "frequency", "motor_current"]
    signal_units = {
        "flow_rate": "bpd",
        "intake_pressure": "psi",
        "discharge_pressure": "psi",
        "motor_temperature": "°C",
        "frequency": "Hz",
        "motor_current": "A"
    }

    features = []
    evidence_items = []
    now_iso = datetime.now(timezone.utc).isoformat()

    if not is_fleet and primary_asset != "FLEET":
        hist = get_history_window_tool(asset_id=primary_asset, signals=target_signals, limit=200)
        for sig in hist.series:
            sig_name = getattr(sig, "signal", getattr(sig, "signal_name", "unknown"))
            sig_unit = getattr(sig, "unit", signal_units.get(sig_name, ""))
            f = compute_signal_features(sig_name, sig.points, unit=sig_unit)
            if f.get("n_points", 0) > 0:
                features.append(f)
                ev = EvidenceCollector.collect_from_historian(
                    asset_id=primary_asset,
                    signal=sig_name,
                    ts_from=f.get("first_ts"),
                    ts_to=f.get("last_ts"),
                    n_points=f["n_points"],
                    stats=f,
                    unit=f["unit"]
                )
                evidence_items.append(ev)

    # 4. Knowledge Graph Evidence (Neo4j / JSON)
    try:
        ga = GraphAdapter()
        fm_traces = ga.trace_cause_effect(query)
        if fm_traces:
            kg_evidence = EvidenceCollector.collect_from_knowledge_graph(primary_asset, fm_traces[:2])
            evidence_items.extend(kg_evidence)
    except Exception:
        pass

    # 5. Build Compact Context for LLM
    telemetry_summary = {
        f["signal"]: {
            "current": f["last"],
            "baseline": f["first"],
            "delta": f["delta"],
            "pct_change": f["pct_change"],
            "slope": f["slope_per_sample"],
            "mean": f["mean"],
            "std": f["std"],
            "unit": f["unit"]
        } for f in features
    }

    # None-safe extraction: asset_ctx is a real AssetContextPayload from AssetService.
    # Individual nameplate fields may be null in the rich seed, so coalesce each field
    # independently rather than only guarding for a missing attribute.
    def _spec(attr: str, default: Any) -> Any:
        val = getattr(asset_ctx, attr, None) if asset_ctx is not None else None
        return val if val is not None else default

    asset_ctx_dict = {
        "asset_id": primary_asset,
        "pump_model": _spec("pump_model", "Unspecified (registry nameplate null)"),
        "motor_hp": _spec("motor_rating_hp", 150),
        "nameplate_amps": _spec("nameplate_current_amps", 24.5),
        "bep_bpd": _spec("be_point_bpd", 1750),
        "installation_depth_ft": _spec("installation_depth_ft", 4500),
    }

    ctx_builder = CompactContextBuilder()
    compact_ctx = ctx_builder.build(
        asset_id=primary_asset,
        objective_id=routed_obj,
        telemetry=telemetry_summary,
        engineering=asset_ctx_dict,
        evidence_refs=[ev.evidence_id for ev in evidence_items]
    )
    compact_ctx["user_question"] = query
    compact_ctx["routed_objective"] = routed_obj

    # 6. LLM Advisory Generation
    # Fail-closed safety gate: operational-control objectives are refused deterministically
    # and never reach the LLM, mirroring the production Supervisor graph. This prevents the
    # model from emitting direct-actuation recommendations under the Advisory-Only lock.
    if routed_obj in HARD_REFUSAL_OBJECTIVES:
        advisory = _build_control_refusal_advisory(query, primary_asset)
        xai = None
    else:
        advisory, xai = llm_adapter.generate_advisory_from_compact_context(
            compact_context=compact_ctx,
            user_query=query,
            run_id=f"RUN-{primary_asset}-{uuid.uuid4().hex[:6]}"
        )

    # 7. Visualization Spec
    vis_spec = build_visualization_spec(primary_asset, routed_obj, features, query)

    latency_ms = (time.monotonic() - t0) * 1000

    return {
        "query": query,
        "asset_id": asset_id,
        "domain": domain,
        "expected_objective": exp_obj,
        "routing": {
            "routed_objective": routed_obj,
            "confidence": route_conf,
            "route_path": route_path,
            "match": (routed_obj == exp_obj) if exp_obj else True
        },
        "telemetry_matrix": [
            {
                "signal": f["signal"],
                "baseline": f["first"],
                "latest": f["last"],
                "delta": f["delta"],
                "pct_change": f["pct_change"],
                "slope": f["slope_per_sample"],
                "sparkline": f["sparkline"],
                "unit": f["unit"]
            } for f in features
        ],
        "evidence_pack": [
            {
                "evidence_id": ev.evidence_id,
                "evidence_type": ev.evidence_type.value if hasattr(ev.evidence_type, "value") else str(ev.evidence_type),
                "authority": ev.authority_level.value if hasattr(ev.authority_level, "value") else str(ev.authority_level),
                "citation": ev.citation,
                "source_deep_link": ev.source_deep_link,
                "statement": ev.statement
            } for ev in evidence_items
        ],
        "advisory": {
            "assessment": getattr(advisory, "assessment", str(advisory)),
            "hypotheses": [
                {
                    "cause": getattr(h, "cause", ""),
                    "confidence": getattr(h, "confidence", 0.0),
                    "reasoning": getattr(h, "reasoning", ""),
                    "supporting_evidence": getattr(h, "supporting_evidence", [])
                } for h in getattr(advisory, "hypotheses", [])
            ],
            "uncertainties": getattr(advisory, "uncertainties", []),
            "recommendation": _extract_recommendation(advisory),
            "verification_steps": _extract_verification_steps(advisory)
        },
        "visualization_spec": vis_spec,
        "latency_ms": round(latency_ms, 1),
        "status": "SUCCESS"
    }


# ═══════════════════════════════════════════════════════════════════════════
# Console Formatter & CLI Runner
# ═══════════════════════════════════════════════════════════════════════════
def print_query_result(res: Dict[str, Any], idx: int, total: int):
    SEP = "=" * 82
    sep = "-" * 82
    print("\n" + SEP)
    r = res["routing"]
    match_tag = "✅ MATCH" if r.get("match") else "⚠️ MISMATCH"
    print(f" [{idx:02d}/{total:02d}] QUERY: \"{res['query']}\"")
    print(f" Asset: {res['asset_id']:<14} | Objective: {r['routed_objective']} ({match_tag}, conf={r['confidence']})")
    print(SEP)

    # 1. Telemetry Matrix
    if res.get("telemetry_matrix"):
        print(" 📈 TELEMETRY MATRIX & STATISTICAL FEATURES")
        print(f" {'Signal':<20} {'First':>8} {'Last':>8} {'Delta':>8} {'%Chg':>7} {'Slope':>8}  {'Trend'}")
        print(f" {'-'*20} {'-'*8} {'-'*8} {'-'*8} {'-'*7} {'-'*8}  {'-'*18}")
        for t in res["telemetry_matrix"]:
            print(f" {t['signal']:<20} {t['baseline']:>8} {t['latest']:>8} {t['delta']:>+8.2f} {t['pct_change']:>+6.1f}% {t['slope']:>+8.4f}  {t['sparkline']}")
        print()

    # 2. Evidence Pack
    if res.get("evidence_pack"):
        print(f" 🔗 EVIDENCE PACK ({len(res['evidence_pack'])} items with Traceable Deep-Links)")
        for ev in res["evidence_pack"]:
            print(f"  • [{ev['evidence_id']}] ({ev['authority']})")
            print(f"    Citation : {ev['citation']}")
            if ev.get("source_deep_link"):
                print(f"    Deep-Link: {ev['source_deep_link']}")
            print(f"    Statement: {ev['statement'][:130]}…")
        print()

    # 3. LLM Advisory
    adv = res["advisory"]
    print(" 💡 AI-GENERATED ADVISORY")
    print(f"  ASSESSMENT: {adv['assessment']}")
    if adv.get("hypotheses"):
        print("  RANKED HYPOTHESES:")
        for i, h in enumerate(adv["hypotheses"], 1):
            conf_pct = int(h['confidence'] * 100) if h['confidence'] <= 1.0 else int(h['confidence'])
            print(f"   {i}. [{conf_pct}% conf] {h['cause']}")
            print(f"      Reasoning : {h['reasoning']}")
            if h.get("supporting_evidence"):
                print(f"      Evidence  : {', '.join(h['supporting_evidence'][:3])}")
    print(f"  RECOMMENDATION: {adv['recommendation']}")
    print()

    # 4. Visualization Spec
    vis = res.get("visualization_spec")
    if vis:
        print(f" 📊 GENERATIVE UI VISUALIZATION MANIFEST: {vis['type']} — \"{vis['title']}\" (ID: {vis['vis_id']})")
    print(f" ⏱️ Execution Latency: {res['latency_ms']} ms")
    print(SEP)


def main():
    ap = argparse.ArgumentParser(description="Master End-to-End Query Execution Pipeline")
    ap.add_argument("--queries-file", "-f", default=str(ROOT_DIR / "queries_catalogue.json"), help="Path to queries_catalogue.json")
    ap.add_argument("--query", "-q", help="Run a single ad-hoc query")
    ap.add_argument("--asset", "-a", default="FS-031", help="Target asset ID")
    ap.add_argument("--objective", "-o", help="Filter queries by objective domain (e.g. OP02, OP08)")
    ap.add_argument("--limit", "-l", type=int, help="Limit number of queries to execute")
    ap.add_argument("--out", default=str(ROOT_DIR / "full_pipeline_results.json"), help="Path to export comprehensive JSON results")
    args = ap.parse_args()

    # Load queries
    if args.query:
        query_items = [{"query": args.query, "asset_id": args.asset, "objective_id": args.objective}]
    else:
        qpath = Path(args.queries_file)
        if not qpath.exists():
            print(f"[-] Queries catalogue not found: {qpath}")
            sys.exit(1)
        with open(qpath, "r", encoding="utf-8") as f:
            query_items = json.load(f)

    if args.objective:
        query_items = [q for q in query_items if args.objective.upper() in q.get("objective_id", "").upper()]

    if args.limit:
        query_items = query_items[:args.limit]

    print("=" * 82)
    print(" ESP APM — MASTER END-TO-END QUERY EXECUTION PIPELINE")
    print(f" Total Queries to Execute: {len(query_items)}")
    print(f" Output JSON Destination  : {args.out}")
    print("=" * 82)

    # Initialize shared components
    registry = ObjectiveRegistry()
    router = IntentRouter(registry=registry)
    asset_svc = AssetService()
    llm_adapter = LLMAdapter()

    results = []
    out_path = Path(args.out)

    for idx, item in enumerate(query_items, 1):
        try:
            res = execute_query_pipeline(item, router, asset_svc, llm_adapter)
            results.append(res)
            print_query_result(res, idx, len(query_items))

            # Incremental JSON save after each query so progress is never lost
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)

        except Exception as ex:
            print(f"[-] Error on query #{idx} (\"{item.get('query')}\"): {ex}")

    print("\n" + "=" * 82)
    print(f" PIPELINE COMPLETE: Successfully processed {len(results)}/{len(query_items)} queries.")
    print(f" Saved full results with Evidence + Visualizations to: {out_path.resolve()}")
    print("=" * 82 + "\n")


if __name__ == "__main__":
    main()
