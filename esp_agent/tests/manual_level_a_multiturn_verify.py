"""
MANUAL verification script — Level A exit criteria (Plan.md)
"real, 2-turn LLM run" — user-run command, ~70s each turn, NOT part of automated pytest suite
because it hits the office LLM server and is slow / timeout-prone in an IDE terminal.

Run yourself on your local terminal (per project convention — faster than IDE-spawned processes):

    cd X:\\TAS\\Agentic_project\\esp_agent
    .venv\\Scripts\\python.exe tests\\manual_level_a_multiturn_verify.py

What this checks (Plan.md Level A exit criteria, verbatim):
  "Status of FSWS-001-A?" -> then "is that bad?" resolves to the same well and a coherent
  follow-up objective, with history visible in the prompt.

Paste the full printed output back for review — do not summarize it yourself, since the
whole point is to check the SAME well is used and the follow-up objective is coherent
(not a re-diagnosis from scratch, not a default-to-OP03 dump).
"""

import sys
import time
import uuid

sys.path.insert(0, ".")

from src.agent.supervisor.user_entry import UserEntryAdapter  # noqa: E402

try:
    from src.memory.conversation_store import ConversationStore
    _HAS_STORE = True
except ModuleNotFoundError:
    _HAS_STORE = False


def main():
    session_id = f"MANUAL-VERIFY-{uuid.uuid4().hex[:8]}"
    asset_id = "FSWS-001-A"
    adapter = UserEntryAdapter()

    print("=" * 78)
    print("LEVEL A MANUAL VERIFICATION — multi-turn implicit well + history")
    print(f"session_id = {session_id}")
    print("=" * 78)

    # --- Turn 1: well-formed query, explicit asset_id ---
    print("\n--- TURN 1 ---")
    q1 = "What is the current status of FSWS-001-A? Is there anything wrong with it?"
    print(f"USER: {q1}")
    t0 = time.time()
    try:
        r1 = adapter.run(user_query=q1, asset_id=asset_id, session_id=session_id,
                          request_id="LEVELA-MANUAL-T1")
    except TypeError:
        print("\n!! UserEntryAdapter.run() does not yet accept session_id — Phase A3 not implemented.")
        print("!! Falling back to no-session call so you can still see baseline turn-1 behavior.")
        r1 = adapter.run(user_query=q1, asset_id=asset_id, request_id="LEVELA-MANUAL-T1")
    dt1 = time.time() - t0
    print(f"ELAPSED: {dt1:.2f}s")
    print(f"ASSESSMENT: {r1.assessment}")
    print(f"DIAGNOSIS: {r1.diagnosis}")
    print(f"CONFIDENCE: {r1.confidence}")

    # --- Turn 2: bare follow-up, NO asset_id, NO explicit well mention ---
    print("\n--- TURN 2 (follow-up, no asset_id given) ---")
    q2 = "is that bad?"
    print(f"USER: {q2}")
    t0 = time.time()
    try:
        r2 = adapter.run(user_query=q2, asset_id=None, session_id=session_id,
                          request_id="LEVELA-MANUAL-T2")
    except TypeError:
        print("\n!! UserEntryAdapter.run() does not yet accept session_id/optional asset_id.")
        print("!! Cannot verify implicit well resolution until Phase A3 lands. Stopping here.")
        return
    dt2 = time.time() - t0
    print(f"ELAPSED: {dt2:.2f}s")
    print(f"ASSESSMENT: {r2.assessment}")
    print(f"DIAGNOSIS: {r2.diagnosis}")
    print(f"CONFIDENCE: {r2.confidence}")

    # --- Verification checks ---
    print("\n" + "=" * 78)
    print("VERIFICATION CHECKS")
    print("=" * 78)

    checks_passed = 0
    checks_total = 0

    checks_total += 1
    if asset_id in str(r2.assessment) or asset_id in str(getattr(r2, "asset_id", "")):
        print(f"[PASS] Turn 2 response references the implicit well ({asset_id}).")
        checks_passed += 1
    else:
        print(f"[FAIL] Turn 2 response does NOT clearly reference {asset_id}. "
              f"Implicit well resolution may not be wired (Phase A3.T1).")

    checks_total += 1
    t2_diag_lower = str(r2.diagnosis).lower()
    if "no significant" not in t2_diag_lower and t2_diag_lower.strip() not in ("", "unknown"):
        print("[PASS] Turn 2 gives a coherent follow-up answer (not a blank/defaulted re-diagnosis).")
        checks_passed += 1
    else:
        print("[FAIL] Turn 2 looks like a fresh/defaulted diagnosis rather than a follow-up "
              "answer grounded in turn 1's finding. Check Phase A2 (router conversation context).")

    if _HAS_STORE:
        checks_total += 1
        store = ConversationStore()
        history = store.get_history(session_id)
        if len(history) >= 4:  # 2 user + 2 assistant turns
            print(f"[PASS] ConversationStore recorded {len(history)} turns for this session.")
            checks_passed += 1
        else:
            print(f"[FAIL] ConversationStore only has {len(history)} turns recorded; expected >= 4.")
        store.clear(session_id)
    else:
        print("[SKIP] ConversationStore not implemented yet (Phase A1) — cannot verify persistence.")

    print(f"\n{checks_passed}/{checks_total} automated checks passed.")
    print("Paste this full output back for review — the objective-coherence check "
          "(is turn 2 actually a follow-up, not a re-diagnosis) needs human judgment too.")


if __name__ == "__main__":
    main()
