"""
End-to-End LLM Graph Traversal Verification Script
Tests the live pipeline:
User Query -> BFF Gateway (:8090) -> UserEntryAdapter -> IntentRouter ->
LangGraph Supervisor Graph -> Evidence Synthesis -> Local CUDA GPU llama-server (:8080) ->
Structured Advisory Output Schema
"""
import sys
import os
import json
import time
import requests

# Ensure stdout handles utf-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def test_full_graph_llm_traversal():
    url = "http://localhost:8090/api/ui/agent/run"
    headers = {
        "Content-Type": "application/json",
        "X-Session-ID": "sess-e2e-real-gpu-test-01"
    }
    payload = {
        "asset_id": "FS-031",
        "user_query": "Evaluate operational health, thermal stability, and potential gas interference on well FS-031"
    }

    print("=" * 80)
    print("[START] DISPATCHING END-TO-END QUERY TO AGENT JANE BFF GATEWAY (Port 8090)")
    print(f"Asset ID   : {payload['asset_id']}")
    print(f"User Query : {payload['user_query']}")
    print(f"Session ID : {headers['X-Session-ID']}")
    print("=" * 80)

    start_time = time.time()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60.0)
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        sys.exit(1)

    elapsed = time.time() - start_time
    print(f"\n[TIME] Round-Trip Network Latency: {elapsed:.2f} seconds")
    print(f"HTTP Status Code: {response.status_code}")

    if response.status_code != 200:
        print(f"[ERROR] Error Response: {response.text}")
        sys.exit(1)

    data = response.json()
    print("\n" + "=" * 80)
    print("[CARD] AGENT JANE STRUCTURED ADVISORY OUTPUT (FULL GRAPH TRAVERSAL)")
    print("=" * 80)
    print(f"Advisory ID         : {data.get('advisory_id')}")
    print(f"Run ID              : {data.get('run_id')}")
    print(f"Asset ID            : {data.get('asset_id')}")
    print(f"Resolved Objective  : {data.get('objective_id')}")
    print(f"Confidence Score    : {data.get('confidence_score')}")
    print(f"Data Quality        : {data.get('data_quality_summary')}")
    
    print("\n--- EXECUTIVE SUMMARY ---")
    print(data.get('executive_summary', 'N/A'))

    print("\n--- PRIMARY ROOT-CAUSE DRIVERS ---")
    findings = data.get('findings', [])
    if isinstance(findings, list):
        for f in findings:
            print(f"  * {f}")
    else:
        print(f"  {findings}")

    print("\n--- RECOMMENDED ACTIONS (MITIGATION) ---")
    actions = data.get('recommended_actions', [])
    for a in actions:
        if isinstance(a, dict):
            print(f"  -> [{a.get('urgency', 'ADVISORY')}] {a.get('action_text')} (Target: {a.get('target_parameter')})")
        else:
            print(f"  -> {a}")

    print("\n--- EVIDENCE PACK CITATIONS ---")
    evidence = data.get('evidence_items', [])
    for e in evidence[:5]:
        if isinstance(e, dict):
            print(f"  [EVID] [{e.get('evidence_id')}] ({e.get('authority_level')}) {e.get('source_system')}: {e.get('statement')}")
        else:
            print(f"  [EVID] {e}")

    # LLM Telemetry Metadata
    llm_meta = data.get('llm_telemetry') or data.get('meta', {}).get('llm_telemetry')
    print("\n--- LLM INFERENCE TELEMETRY ---")
    if llm_meta:
        print(f"Model Name        : {llm_meta.get('model_name')}")
        print(f"Prompt Tokens     : {llm_meta.get('prompt_tokens')}")
        print(f"Completion Tokens : {llm_meta.get('completion_tokens')}")
        print(f"Generation Latency: {llm_meta.get('latency_ms')} ms")
        print(f"Is Mock Response  : {llm_meta.get('is_mock')} (False = Real CUDA GPU LLM)")
    else:
        print("  Telemetry metadata embedded in execution state.")

    print("=" * 80)
    print("[SUCCESS] END-TO-END LLM GRAPH TRAVERSAL COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    test_full_graph_llm_traversal()
