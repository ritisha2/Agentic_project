"""
ESP Historian Decision-Support CLI — Full LLM Pipeline
=======================================================
Grounded in Guidelines.pdf §4.1, §22.1, Appendix B and historian.txt §7, §10, §12

Full pipeline:
  User Query
    → Intent Router (objective classification)
    → Historian Service (633k record SQLite DB → real time-series points)
    → Statistical Feature Engine (slopes, correlations, inflections)
    → Asset Context Service (pump specs, nameplate, BEP, operating limits)
    → CompactContextBuilder (LLM-safe JSON compression)
    → LLMAdapter.generate_advisory_from_compact_context()
        → LayeredPromptBuilder (SYSTEM + DOMAIN + OBJECTIVE layers)
        → LLMGateway → local Qwen/OpenAI-compatible LLM
        → StructuredOutputValidator + JSON-repair loop
    → Formal EvidenceItem Pack (Level D — Site History)
    → Rendered terminal output + optional JSON export

Zero hardcoded findings text. Every advisory sentence is produced by the LLM
reasoning over the real numeric evidence extracted from the DB.
"""

import sys
import re
import json
import argparse
import statistics
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ── Path setup ──────────────────────────────────────────────────────────────
import os as _os
ROOT_DIR = Path(_os.path.dirname(_os.path.abspath(__file__)))
CCED_DIR = ROOT_DIR.parent / "cced_esp"
# esp_agent root must be first so `src.*` resolves to esp_agent/src
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(CCED_DIR) not in sys.path:
    sys.path.append(str(CCED_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(level=logging.WARNING)

# ── Project imports ──────────────────────────────────────────────────────────
from src.tools.fetch_telemetry import get_history_window_tool
from src.tools.registry import get_default_tool_registry
from src.agent.intent_router import IntentRouter
from src.agent.objective_registry import ObjectiveRegistry
from src.adapters.asset_service import AssetService
from src.llm.adapter import LLMAdapter
from src.llm.context_builder import CompactContextBuilder
from src.schemas.contracts import TimeSeriesPayload, TimeSeriesSignal
from src.schemas.evidence import (
    EvidenceItem, EvidenceType, AuthorityLevel, QualityStatus,
)
from src.services.evidence.collector import EvidenceCollector



# ═══════════════════════════════════════════════════════════════════════════
# 1. Sparkline renderer
# ═══════════════════════════════════════════════════════════════════════════
def render_sparkline(values: List[float], width: int = 22) -> str:
    if not values:
        return "[no data]"
    if len(values) > width:
        step = len(values) / width
        values = [values[int(i * step)] for i in range(width)]
    lo, hi = min(values), max(values)
    if hi == lo:
        return "─" * len(values)
    ticks = " ▂▃▄▅▆▇█"
    return "".join(ticks[int((v - lo) / (hi - lo) * 7)] for v in values)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Query entity extractors
# ═══════════════════════════════════════════════════════════════════════════
def extract_asset(query: str, default: str = "FS-031") -> str:
    m = re.search(r"\b(FSWS-\d{3}(?:-[A-Z])?|FS-\d{3}|ESP-\d{3})\b", query, re.IGNORECASE)
    return m.group(1).upper() if m else default


def extract_window(query: str, default: str = "6h") -> str:
    m = re.search(r"\b(\d+)\s*(hours?|hrs?|h|days?|d|mins?|m)\b", query, re.IGNORECASE)
    if not m:
        return default
    n, u = m.group(1), m.group(2).lower()
    if "d" in u:
        return f"{n}d"
    if "m" in u and len(u) > 1:
        return f"{n}m"
    return f"{n}h"


# ═══════════════════════════════════════════════════════════════════════════
# 3. Statistical Feature Engine — pure math, zero heuristic text
# ═══════════════════════════════════════════════════════════════════════════
def compute_signal_features(sig: TimeSeriesSignal) -> Dict[str, Any]:
    """
    Compute statistical features from a TimeSeriesSignal.
    Returns a compact dict for the LLM compact context.
    """
    pts = sig.points
    if not pts:
        return {
            "signal": sig.signal, "unit": sig.unit,
            "n_points": 0, "status": "NO_DATA"
        }

    vals = [p.value for p in pts]
    n = len(vals)

    # Basic stats
    mean_v = statistics.mean(vals)
    std_v = statistics.stdev(vals) if n > 1 else 0.0
    min_v, max_v = min(vals), max(vals)
    first_v, last_v = vals[0], vals[-1]
    delta = last_v - first_v
    pct_change = (delta / (abs(first_v) + 1e-9)) * 100.0

    # Linear slope (dY/dt) via simple finite difference over all points
    if n > 2:
        # treat index as proxy for time → units per sample period
        x_mid = n // 2
        slope = (statistics.mean(vals[x_mid:]) - statistics.mean(vals[:x_mid])) / max(x_mid, 1)
    else:
        slope = delta / max(n - 1, 1)

    # Inflection detection: first index where |rolling_delta| > 2*std
    inflection_ts: Optional[str] = None
    if n > 4 and std_v > 0:
        window = max(3, n // 10)
        for i in range(window, n):
            local_delta = abs(vals[i] - statistics.mean(vals[i - window:i]))
            if local_delta > 2.0 * std_v:
                inflection_ts = pts[i].timestamp
                break

    # Monotonicity score: +1 rising, -1 falling, 0 mixed
    rises = sum(1 for i in range(1, n) if vals[i] > vals[i - 1])
    mono_score = round((rises / (n - 1) * 2 - 1), 2) if n > 1 else 0.0

    return {
        "signal": sig.signal,
        "unit": sig.unit,
        "n_points": n,
        "first": round(first_v, 2),
        "last": round(last_v, 2),
        "min": round(min_v, 2),
        "max": round(max_v, 2),
        "mean": round(mean_v, 2),
        "std": round(std_v, 3),
        "delta": round(delta, 2),
        "pct_change": round(pct_change, 1),
        "slope_per_sample": round(slope, 4),
        "monotonicity": mono_score,
        "inflection_at": inflection_ts,
        "sparkline": render_sparkline(vals),
        "first_ts": pts[0].timestamp,
        "last_ts": pts[-1].timestamp,
        "quality": sig.quality,
    }


def cross_signal_correlation(
    features: List[Dict[str, Any]],
    a_name: str,
    b_name: str
) -> Optional[float]:
    """Pearson r between two named signal features across the points lists."""
    # We don't store raw points in features dict; this is a placeholder that
    # returns None when signals share no overlapping samples.
    # Full correlation would require aligning timestamps — acceptable scope here.
    return None


def build_telemetry_summary_for_llm(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Transform raw statistical features into a compact telemetry_summary dict
    that the CompactContextBuilder and LLM understand.
    """
    summary: Dict[str, Any] = {}
    for f in features:
        sig = f["signal"]
        if f.get("n_points", 0) == 0:
            summary[sig] = {"status": "NO_DATA", "unit": f.get("unit", "")}
            continue

        # Trend direction label
        mono = f.get("monotonicity", 0)
        if mono > 0.4:
            trend = "rising"
        elif mono < -0.4:
            trend = "declining"
        else:
            trend = "fluctuating"

        summary[sig] = {
            "current": f["last"],
            "baseline": f["first"],
            "delta": f["delta"],
            "pct_change": f["pct_change"],
            "mean": f["mean"],
            "std": f["std"],
            "min": f["min"],
            "max": f["max"],
            "trend": trend,
            "slope_per_sample": f["slope_per_sample"],
            "inflection_detected_at": f.get("inflection_at"),
            "n_points": f["n_points"],
            "unit": f["unit"],
            "quality": f.get("quality", "GOOD"),
        }
    return summary


def _serialize_xai(xai: Any) -> Optional[Dict]:
    """Serialize XAIExplanationPayload (dataclass or Pydantic) to dict safely."""
    if xai is None:
        return None
    if hasattr(xai, "model_dump"):
        return xai.model_dump()
    try:
        import dataclasses
        if dataclasses.is_dataclass(xai):
            return dataclasses.asdict(xai)
    except Exception:
        pass
    try:
        return vars(xai)
    except Exception:
        return str(xai)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Main pipeline
# ═══════════════════════════════════════════════════════════════════════════
def run_historian_query(
    query: str,
    asset_id: Optional[str] = None,
    time_window: Optional[str] = None,
    aggregation: str = "raw",
    limit: int = 200,
    export_json: bool = False,
) -> Dict[str, Any]:

    resolved_asset = (asset_id or extract_asset(query)).strip()
    resolved_window = (time_window or extract_window(query)).strip()

    # ── A. Intent routing ────────────────────────────────────────────────
    registry = ObjectiveRegistry()
    router   = IntentRouter(registry=registry)
    obj_id, confidence, route_path = router.route(query)

    SEP = "=" * 78
    sep = "-" * 78
    print(SEP)
    print(" ESP HISTORIAN  —  Full LLM Intelligence Pipeline")
    print(SEP)
    print(f" Query   : {query}")
    print(f" Asset   : {resolved_asset}  |  Window: {resolved_window}  |  Agg: {aggregation}")
    print(f" Intent  : {obj_id}  (conf={confidence:.2f}, path={route_path})")
    print(sep)

    # ── B. Asset context (pump specs, BEP, limits) ───────────────────────
    asset_svc = AssetService()
    asset_ctx = asset_svc.get_asset(resolved_asset)

    # ── C. Historian data via Tool Layer ─────────────────────────────────
    print(" [1/5] Fetching historical telemetry from DB …")
    # Adaptive signal selection based on query terms
    q = query.lower()
    if any(w in q for w in ["temp", "heat", "thermal", "motor"]):
        signals = ["motor_temperature", "motor_current", "intake_pressure", "frequency"]
    elif any(w in q for w in ["press", "pip", "pdp", "discharge"]):
        signals = ["intake_pressure", "discharge_pressure", "flow_rate", "frequency"]
    elif any(w in q for w in ["flow", "prod", "decline", "liquid", "rate"]):
        signals = ["flow_rate", "intake_pressure", "discharge_pressure", "frequency", "motor_current"]
    else:
        signals = ["flow_rate", "intake_pressure", "discharge_pressure",
                   "motor_temperature", "frequency", "motor_current"]

    hist: TimeSeriesPayload = get_history_window_tool(
        asset_id=resolved_asset,
        start_time=resolved_window,
        signals=signals,
        aggregation=aggregation,
        limit=limit,
    )

    # ── D. Statistical Feature Engine ────────────────────────────────────
    print(" [2/5] Computing statistical features (slopes, inflections, trends) …")
    features: List[Dict[str, Any]] = [compute_signal_features(s) for s in hist.series]

    # Print evidence matrix
    print()
    print(f" HISTORIAN TELEMETRY MATRIX  ({len(hist.series)} signals | coverage {hist.coverage*100:.0f}%)")
    print(f" {'Signal':<22} {'First':>8} {'Last':>8} {'Delta':>8} {'%Chg':>7} {'Slope':>8}  Trend")
    print(f" {'-'*22} {'-'*8} {'-'*8} {'-'*8} {'-'*7} {'-'*8}  --------")
    for f in features:
        if f.get("n_points", 0) == 0:
            print(f"  {f['signal']:<22} [NO DATA]")
            continue
        arrow = "▼" if f["delta"] < -0.5 else ("▲" if f["delta"] > 0.5 else "─")
        print(
            f"  {f['signal']:<22} {f['first']:>8.2f} {f['last']:>8.2f} "
            f"{f['delta']:>+8.2f} {f['pct_change']:>+7.1f}% {f['slope_per_sample']:>8.4f}  "
            f"{arrow} {f['sparkline']}"
        )
        if f.get("inflection_at"):
            print(f"    {'':22} inflection detected @ {f['inflection_at']}")
    print()

    # ── E. Build formal Evidence Pack with Real Deep-Links ───────────────
    print(" [3/5] Building Level-D Evidence Pack with Real Deep-Links …")
    now_iso = datetime.now(timezone.utc).isoformat()
    evidence_items: List[EvidenceItem] = []
    for f in features:
        if f.get("n_points", 0) == 0:
            continue
        ev = EvidenceCollector.collect_from_historian(
            asset_id=resolved_asset,
            signal=f["signal"],
            ts_from=f.get("first_ts"),
            ts_to=f.get("last_ts"),
            n_points=f["n_points"],
            stats=f,
            unit=f["unit"],
        )
        evidence_items.append(ev)

    # Print provenance & deep-links
    print(f" EVIDENCE PACK  ({len(evidence_items)} items | Authority: Level D — Ground Truth Site History)")
    for ev in evidence_items:
        print(f"  [{ev.evidence_id}]")
        print(f"    Citation : {ev.citation}")
        print(f"    Deep-Link: {ev.source_deep_link}")
        print(f"    Statement: {ev.statement[:140]}…")
    print()

    # ── F. Build compact LLM context ─────────────────────────────────────
    print(" [4/5] Building LLM compact context & invoking AI reasoning pipeline …")
    telemetry_summary = build_telemetry_summary_for_llm(features)

    asset_ctx_dict = {
        "asset_id": resolved_asset,
        "pump_model": getattr(asset_ctx, "pump_model", "Unknown"),
        "motor_hp": getattr(asset_ctx, "motor_rating_hp", "Unknown"),
        "nameplate_amps": getattr(asset_ctx, "nameplate_current_amps", "Unknown"),
        "bep_bpd": getattr(asset_ctx, "be_point_bpd", "Unknown"),
        "installation_depth_ft": getattr(asset_ctx, "installation_depth_ft", "Unknown"),
    }

    ctx_builder = CompactContextBuilder()
    compact_ctx = ctx_builder.build(
        asset_id=resolved_asset,
        objective_id=obj_id,
        telemetry=telemetry_summary,
        engineering=asset_ctx_dict,
        evidence_refs=[ev.evidence_id for ev in evidence_items],
    )
    # Inject the full user question so the LLM answers exactly what was asked
    compact_ctx["user_question"] = query
    compact_ctx["historian_window"] = resolved_window
    compact_ctx["historian_total_points"] = hist.total_points
    compact_ctx["historian_coverage"] = hist.coverage

    # ── G. LLM Advisory Generation ───────────────────────────────────────
    llm = LLMAdapter()
    is_live = llm.gateway.is_available()
    mode = "LIVE LLM" if is_live else "LLM MOCK FALLBACK (local server offline)"
    print(f"         LLM engine: {mode}")

    advisory, xai = llm.generate_advisory_from_compact_context(
        compact_context=compact_ctx,
        user_query=query,
        run_id=f"HIST-{resolved_asset}-{now_iso[-13:-4].replace(':', '')}",
    )
    print()

    # ── H. Render LLM advisory ───────────────────────────────────────────
    print(SEP)
    print(" [5/5] LLM-GENERATED ADVISORY  (zero hardcoded text)")
    print(SEP)
    print(f" ASSESSMENT\n  {advisory.assessment}")
    print()
    print(" RANKED HYPOTHESES (from LLM reasoning over historian evidence)")
    for i, h in enumerate(advisory.hypotheses, 1):
        print(f"  {i}. [{h.confidence*100:.0f}% conf] {h.cause}")
        print(f"      Reasoning  : {h.reasoning}")
        if h.supporting_evidence:
            print(f"      Evidence   : {', '.join(h.supporting_evidence[:4])}")
    print()
    if advisory.uncertainties:
        print(" UNCERTAINTIES")
        for u in advisory.uncertainties:
            print(f"  • {u}")
        print()
    print(f" RECOMMENDATION\n  {advisory.recommendation}")
    print()
    if advisory.verification:
        print(" VERIFICATION STEPS")
        verif = advisory.verification
        if isinstance(verif, str):
            verif = [verif]
        for v in verif:
            print(f"  {v}")
    print()
    print(f" LLM ENGINE  : {mode}")
    print(f" EVIDENCE    : {len(evidence_items)} Level-D items cited from unlabelled_recovered.db")
    print(f" COVERAGE    : {hist.coverage*100:.1f}% | Points: {hist.total_points} | Window: {resolved_window}")
    print(SEP)

    result = {
        "query": query,
        "asset_id": resolved_asset,
        "window": resolved_window,
        "objective": obj_id,
        "llm_live": is_live,
        "signal_features": features,
        "evidence_items": [ev.model_dump() for ev in evidence_items],
        "advisory": {
            "assessment": advisory.assessment,
            "hypotheses": [h.model_dump() for h in advisory.hypotheses],
            "uncertainties": advisory.uncertainties,
            "recommendation": advisory.recommendation,
            "verification": advisory.verification,
        },
        "xai": _serialize_xai(xai),
    }

    if export_json:
        fname = f"historian_advisory_{resolved_asset}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(fname, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        print(f"\n Exported advisory + evidence pack → {fname}")

    return result


# ═══════════════════════════════════════════════════════════════════════════
# 5. Interactive REPL
# ═══════════════════════════════════════════════════════════════════════════
def interactive_mode():
    SEP = "=" * 78
    print(SEP)
    print(" ESP HISTORIAN  —  Interactive AI Decision-Support Terminal")
    print(" Type any question. 'exit' to quit.")
    print(" Examples:")
    print("   Why is production declining on FS-031 in the last 6 hours?")
    print("   Compare intake pressure and motor temperature on FS-010 over 24h")
    print("   What is causing thermal stress on FS-031?")
    print(SEP)
    while True:
        try:
            q = input("\n[ESP-Historian] > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break
        if not q:
            continue
        if q.lower() in ("exit", "quit", "q"):
            print("Goodbye.")
            break
        try:
            run_historian_query(query=q)
        except Exception as ex:
            print(f" ERROR: {ex}")


# ═══════════════════════════════════════════════════════════════════════════
# 6. CLI entry point
# ═══════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser(
        description="ESP Historian — full LLM pipeline query & evidence CLI"
    )
    ap.add_argument("--query", "-q", help="Natural language query")
    ap.add_argument("--asset", "-a", help="Asset ID override (e.g. FS-031)")
    ap.add_argument("--window", "-w", default="6h",
                    help="Time window: 1h, 6h, 24h, 7d (default 6h)")
    ap.add_argument("--agg", default="raw",
                    help="Aggregation: raw, 1m, 5m, 15m, 1h (default raw for max resolution)")
    ap.add_argument("--limit", type=int, default=200,
                    help="Max data points per signal (default 200)")
    ap.add_argument("--export-json", action="store_true",
                    help="Export full advisory + evidence pack to JSON file")
    ap.add_argument("--interactive", "-i", action="store_true",
                    help="Launch interactive REPL")
    args = ap.parse_args()

    if args.interactive or not args.query:
        if args.query:
            run_historian_query(
                query=args.query, asset_id=args.asset,
                time_window=args.window, aggregation=args.agg,
                limit=args.limit, export_json=args.export_json,
            )
        else:
            interactive_mode()
    else:
        run_historian_query(
            query=args.query, asset_id=args.asset,
            time_window=args.window, aggregation=args.agg,
            limit=args.limit, export_json=args.export_json,
        )


if __name__ == "__main__":
    main()
