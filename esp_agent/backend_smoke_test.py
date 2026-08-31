"""
Backend smoke test for the esp_agent Gateway (:8090) — run with all 4 servers up.
Note: LLM_OFFLINE is disabled by project policy (see src/llm/gateway.py) — the real
local LLM (llama.cpp on :8080) is always used regardless of this env var.

Checks, in order:
  1. Health   : gateway, MCP tool layer, and the local LLM server (:8080)
  2. Routing  : "hi" -> OP07_GENERAL_INQUIRY, and a diagnostic query -> a different objective
  3. LLM      : whether the REAL LLM answered or it fell back to the offline mock (via provenance)
  4. Streaming: the /agent/stream NDJSON pipeline (status -> advisory -> text_delta -> chart -> done)
  5. MCP      : a governed tool call over HTTP + an RBAC denial (403)

Usage:
    cd X:\\TAS\\Agentic_project\\esp_agent
    .venv\\Scripts\\python.exe backend_smoke_test.py
    # optional overrides:
    .venv\\Scripts\\python.exe backend_smoke_test.py --base http://127.0.0.1:8090 --asset FS-010
"""

import argparse
import json
import sys
import time

try:
    import httpx
except ImportError:
    print("httpx not available in this interpreter. Run with the venv python:\n"
          r"   .venv\Scripts\python.exe backend_smoke_test.py")
    sys.exit(1)

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[info]"


def hr(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def check_health(base, llm_url):
    hr("1. HEALTH CHECKS")
    # Only the gateway itself is a hard gate. The MCP layer + LLM are reported but non-fatal
    # so the routing / LLM / streaming tests always run.
    gateway_ok = False
    try:
        r = httpx.get(f"{base}/api/ui/health", timeout=10.0)
        gateway_ok = r.status_code == 200
        print(f"  {PASS if gateway_ok else FAIL} gateway    {base}/api/ui/health -> {r.status_code} {r.json()}")
    except Exception as e:
        print(f"  {FAIL} gateway    {base}/api/ui/health -> {e}")

    try:
        r = httpx.get(f"{base}/api/mcp/health", timeout=15.0)
        good = r.status_code == 200
        print(f"  {PASS if good else FAIL} mcp layer  {base}/api/mcp/health -> {r.status_code} "
              f"{r.json() if good else '(route missing/timeout — restart gateway to load MCP routes)'}")
    except Exception as e:
        print(f"  {INFO} mcp layer  {base}/api/mcp/health -> {e}  (non-fatal; continuing)")

    # LLM server (informational — the agent still works via mock if this is down)
    llm_ok = False
    for probe in [llm_url.replace("/v1", "") + "/health", f"{llm_url}/models"]:
        try:
            r = httpx.get(probe, timeout=3.0)
            if r.status_code == 200:
                llm_ok = True
                print(f"  {PASS} llm server {probe} -> 200 (LLM reachable)")
                break
        except Exception:
            continue
    if not llm_ok:
        print(f"  {INFO} llm server not reachable at {llm_url} — agent will use offline mock text.")
    return gateway_ok


def run_query(base, asset, query, timeout=180.0):
    body = {"user_query": query, "asset_id": asset}
    r = httpx.post(f"{base}/api/ui/agent/run", json=body, timeout=timeout)
    r.raise_for_status()
    return r.json()


def check_routing_and_llm(base, asset):
    hr("2 + 3. OBJECTIVE ROUTING + LLM vs MOCK (SINGLE-ASSET & FLEET)")
    cases = [
        ("hi", "OP07_GENERAL_INQUIRY"),
        ("who are you", "OP07_GENERAL_INQUIRY"),
        ("diagnose motor overheating and high vibration on FS-010", "OP03_FAULT_DIAGNOSIS"),
        ("why is production declining on this well", "OP02_PRODUCTION_DECLINE_RCA"),
        ("what if I increase frequency by 2 Hz on FS-010", "OP02_PRODUCTION_DECLINE_RCA"),
        ("list all assets in the fleet", "OP08_FLEET_INVENTORY"),
        ("rank fleet production upside across all wells", "OP09_FLEET_PRODUCTION_OPTIMIZATION"),
        ("rank fleet maintenance urgency", "OP11_FLEET_MAINTENANCE_PRIORITY"),
    ]
    seen_objectives = set()
    for query, expected in cases:
        try:
            t0 = time.time()
            resp = run_query(base, asset, query)
            dt = time.time() - t0
            adv = resp.get("advisory", {})
            obj = resp.get("objective_id", "?")
            prov = " | ".join(adv.get("provenance", []))
            is_mock = "MOCK" in prov.upper() or "OFFLINE" in prov.upper()
            seen_objectives.add(obj)

            tag = PASS
            note = ""
            if expected and obj != expected:
                tag = FAIL
                note = f"(expected {expected})"

            print(f"\n  {tag} query={query!r} {note}")
            print(f"        objective : {obj}")
            print(f"        latency   : {dt:.1f}s")
            print(f"        llm_source: {'OFFLINE MOCK' if is_mock else 'REAL LLM'}  ({prov[:80]})")
            print(f"        assessment: {(adv.get('assessment') or '')[:110]}")
            print(f"        diagnosis : {(adv.get('diagnosis') or '')[:110]}")
            print(f"        confidence: {adv.get('confidence')}")
        except Exception as e:
            print(f"  {FAIL} query={query!r} -> {e}")

    print(f"\n  {INFO} distinct objectives observed across queries: {sorted(seen_objectives)}")
    if len(seen_objectives) > 1:
        print(f"  {PASS} objective routing changes per query.")
    else:
        print(f"  {FAIL} all queries routed to the same objective — routing may not be working.")


def check_streaming(base, asset, query="diagnose intake gas interference", timeout=180.0):
    hr("4. NDJSON STREAMING PIPELINE  (/api/ui/agent/stream)")
    body = {"user_query": query, "asset_id": asset}
    event_types = []
    text_parts = []
    chart_seen = False
    advisory_seen = False
    try:
        with httpx.stream("POST", f"{base}/api/ui/agent/stream", json=body, timeout=timeout) as r:
            if r.status_code != 200:
                print(f"  {FAIL} stream returned HTTP {r.status_code}")
                return
            for line in r.iter_lines():
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                except Exception:
                    continue
                etype = evt.get("type")
                event_types.append(etype)
                if etype == "text_delta":
                    text_parts.append(evt.get("delta", ""))
                elif etype == "advisory":
                    advisory_seen = True
                elif etype == "generative_ui":
                    chart_seen = True
    except Exception as e:
        print(f"  {FAIL} streaming error: {e}")
        return

    ordered = []
    for t in event_types:
        if not ordered or ordered[-1] != t:
            ordered.append(t)
    full_text = "".join(text_parts)
    print(f"  event sequence : {ordered}")
    print(f"  advisory event : {PASS if advisory_seen else FAIL}")
    print(f"  chart event    : {PASS if chart_seen else FAIL}")
    print(f"  done event     : {PASS if 'done' in event_types else FAIL}")
    print(f"  streamed text  : {len(full_text)} chars")
    safe_text = full_text[:600].encode('ascii', 'replace').decode('ascii')
    print("  " + safe_text.replace("\n", "\n  "))


def check_mcp(base, asset):
    hr("5. MCP TOOL LAYER OVER HTTP")
    # tool list
    try:
        r = httpx.get(f"{base}/api/mcp/tools", timeout=10.0)
        print(f"  {PASS if r.status_code==200 else FAIL} GET /api/mcp/tools -> {r.status_code}, count={r.json().get('count')}")
    except Exception as e:
        print(f"  {FAIL} tool list -> {e}")

    # governed invoke (allowed)
    try:
        r = httpx.post(f"{base}/api/mcp/tools/calculate_tdh/invoke",
                       json={"arguments": {"pdp_psi": 2100, "pip_psi": 350, "fluid_sg": 0.85},
                             "objective_id": "OP02_PRODUCTION_DECLINE_RCA"}, timeout=15.0)
        print(f"  {PASS if r.status_code==200 else FAIL} invoke calculate_tdh -> {r.status_code}, result={r.json().get('result')}")
    except Exception as e:
        print(f"  {FAIL} invoke calculate_tdh -> {e}")

    # RBAC denial (simulate under general-inquiry objective -> expect 403)
    try:
        r = httpx.post(f"{base}/api/mcp/tools/simulate_frequency_change/invoke",
                       json={"arguments": {"asset_id": asset, "target_frequency_hz": 55},
                             "objective_id": "OP07_GENERAL_INQUIRY"}, timeout=15.0)
        good = r.status_code == 403
        print(f"  {PASS if good else FAIL} RBAC denial (simulate under OP07) -> {r.status_code} (expect 403)")
    except Exception as e:
        print(f"  {FAIL} RBAC check -> {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8090", help="Agent gateway base URL")
    ap.add_argument("--asset", default="FS-010", help="Asset ID to test with")
    ap.add_argument("--llm", default="http://localhost:8080/v1", help="Local LLM server base URL")
    args = ap.parse_args()

    print(f"Backend smoke test -> {args.base}  (asset {args.asset})")
    if not check_health(args.base, args.llm):
        print(f"\n{FAIL} Gateway itself is unreachable on {args.base} — is run_agent_server.py running? Aborting.")
        sys.exit(1)
    print(f"\n  {INFO} gateway reachable — continuing with routing / LLM / streaming tests "
          f"(MCP-layer failures above are non-fatal).")

    check_routing_and_llm(args.base, args.asset)
    check_streaming(args.base, args.asset)
    check_mcp(args.base, args.asset)

    print("\n" + "=" * 70)
    print("Smoke test complete. Review [PASS]/[FAIL] markers above.")
    print("Tip: 'llm_source: REAL LLM' confirms the gateway is actually hitting :8080.")
    print("=" * 70)


if __name__ == "__main__":
    main()
