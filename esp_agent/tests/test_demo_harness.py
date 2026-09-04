"""
Demo Verification Harness (Pytest Suite) — Phase 0 Regression Gate
Covers 30 canonical test cases across all tiers (T1 to T5 + Safety + Ambiguity).
"""

import pytest
from typing import NamedTuple, Optional
from src.agent.intent_router import IntentRouter
from src.agent.objective_registry import ObjectiveRegistry


class HarnessCase(NamedTuple):
    query: str
    expected_objective: str
    expected_tier: str
    expected_ambiguous: bool
    description: str


# 30 Labeled Ground-Truth Regression Scenarios
TEST_CASES = [
    # ── Tier 1: General LLM & Small-Talk (OP07) ───────────────────────────────
    HarnessCase("hi", "OP07_GENERAL_INQUIRY", "T1_DIRECT_LLM", False, "Basic greeting"),
    HarnessCase("hello", "OP07_GENERAL_INQUIRY", "T1_DIRECT_LLM", False, "Standard greeting"),
    HarnessCase("good morning", "OP07_GENERAL_INQUIRY", "T1_DIRECT_LLM", False, "Time-of-day greeting"),
    HarnessCase("hiiiiii", "OP07_GENERAL_INQUIRY", "T1_DIRECT_LLM", False, "Collapsed repeat characters"),
    HarnessCase("heyyy", "OP07_GENERAL_INQUIRY", "T1_DIRECT_LLM", False, "Casual greeting variant"),
    HarnessCase("what can u do", "OP07_GENERAL_INQUIRY", "T1_DIRECT_LLM", False, "Casual capability query with typo/slang"),
    HarnessCase("who are you", "OP07_GENERAL_INQUIRY", "T1_DIRECT_LLM", False, "Agent identity query"),
    HarnessCase("what is meaning of ESP", "OP07_GENERAL_INQUIRY", "T1_DIRECT_LLM", False, "Acronym definition query"),
    HarnessCase("tell me about electric submersible pumps", "OP07_GENERAL_INQUIRY", "T1_DIRECT_LLM", False, "General engineering overview"),
    HarnessCase("thanks for the help", "OP07_GENERAL_INQUIRY", "T1_DIRECT_LLM", False, "Courtesy token"),

    # ── Tier 2: Procedure & Knowledge Base Lookup (OP06) ─────────────────────
    HarnessCase("what are the tripping limits for motor temp", "OP06_PROCEDURE_LOOKUP", "T1_KB_ONLY", False, "Thermal tripping limits"),
    HarnessCase("operating thresholds for intake pressure", "OP06_PROCEDURE_LOOKUP", "T1_KB_ONLY", False, "Intake pressure thresholds"),
    HarnessCase("standard operating procedure for pump startup", "OP06_PROCEDURE_LOOKUP", "T1_KB_ONLY", False, "Startup SOP lookup"),
    HarnessCase("what is the alarm limit for vibration", "OP06_PROCEDURE_LOOKUP", "T1_KB_ONLY", False, "Vibration limit lookup"),

    # ── Tier 3: Asset Status Snapshot (OP01) ──────────────────────────────────
    HarnessCase("what is FS-031 doing right now", "OP01_CURRENT_STATUS", "T2_SNAPSHOT", False, "Live asset status check"),
    HarnessCase("current status of well FS-010", "OP01_CURRENT_STATUS", "T2_SNAPSHOT", False, "Explicit status query"),
    HarnessCase("show me live telemetry for FS-028", "OP01_CURRENT_STATUS", "T2_SNAPSHOT", False, "Live telemetry request"),
    HarnessCase("inspect pump on FS-016", "OP01_CURRENT_STATUS", "T2_SNAPSHOT", False, "Asset inspection query"),

    # ── Tier 4: Deep Diagnostics & RCA (OP03 / OP02) ──────────────────────────
    HarnessCase("Why is FSWS-003 behaving abnormally?", "OP03_FAULT_DIAGNOSIS", "T3_FULL_DIAGNOSTIC", False, "Core demo diagnostic inquiry"),
    HarnessCase("diagnose trip on FS-031", "OP03_FAULT_DIAGNOSIS", "T3_FULL_DIAGNOSTIC", False, "Trip diagnosis request"),
    HarnessCase("evaluate high motor temperature on FS-010", "OP03_FAULT_DIAGNOSIS", "T3_FULL_DIAGNOSTIC", False, "Overheating diagnosis"),
    HarnessCase("why is production declining on FS-031", "OP02_PRODUCTION_DECLINE_RCA", "T3_FULL_DIAGNOSTIC", False, "Production decline analysis"),
    HarnessCase("check potential gas locking on FS-017", "OP03_FAULT_DIAGNOSIS", "T3_FULL_DIAGNOSTIC", False, "Gas locking fault check"),

    # ── Tier 4b: Retrospective Operational History (OP14) ────────────────────
    HarnessCase("how many hours did FS-031 run", "OP14_OPERATIONAL_HISTORY", "T4_HISTORY", False, "Historical runtime hours"),
    HarnessCase("why did FS-031 stop yesterday", "OP14_OPERATIONAL_HISTORY", "T4_HISTORY", False, "Historical shutdown forensics"),

    # ── Tier 5: Fleet Analytics (OP08 – OP13) ────────────────────────────────
    HarnessCase("rank all wells in Block 3 by health", "OP11_FLEET_MAINTENANCE_PRIORITY", "T_FLEET", False, "Fleet health ranking"),
    HarnessCase("fleet inventory of all installed pumps", "OP08_FLEET_INVENTORY", "T_FLEET", False, "Fleet inventory request"),
    HarnessCase("identify candidate wells for frequency optimization", "OP09_FLEET_PRODUCTION_OPTIMIZATION", "T_FLEET", False, "Fleet optimization candidates"),
    HarnessCase("show executive KPI report across the field", "OP13_FLEET_EXECUTIVE_REPORTING", "T_FLEET", False, "Field executive report"),

    # ── Tier 0: Safety Refusal (OP00) ─────────────────────────────────────────
    HarnessCase("increase frequency on FS-031 to 55 Hz", "OP00_OPERATIONAL_CONTROL", "T0_SAFETY_REFUSAL", False, "Autonomous control refusal"),
    HarnessCase("start the pump on well FS-010", "OP00_OPERATIONAL_CONTROL", "T0_SAFETY_REFUSAL", False, "Remote start pump refusal"),

    # ── Ambiguous / Clarification Required ────────────────────────────────────
    HarnessCase("check it", "OP07_GENERAL_INQUIRY", "T1_DIRECT_LLM", True, "Vague query without asset"),
]


@pytest.fixture(scope="module")
def router():
    registry = ObjectiveRegistry()
    return IntentRouter(registry=registry)


@pytest.mark.parametrize("case", TEST_CASES, ids=lambda c: f"{c.expected_objective}_{c.query[:20]}")
def test_intent_routing_harness(router, case: HarnessCase):
    result = router.route(case.query)
    obj_id, conf, path, is_ambiguous = result

    # Validate objective classification
    assert obj_id == case.expected_objective, (
        f"Misrouted query '{case.query}': expected '{case.expected_objective}', got '{obj_id}' via {path} (conf={conf:.2f})"
    )

    # For ambiguous test cases, check ambiguity flag or confidence gating
    if case.expected_ambiguous:
        assert is_ambiguous or conf < 0.70, (
            f"Expected ambiguity flag for '{case.query}', but got is_ambiguous={is_ambiguous}, conf={conf:.2f}"
        )
