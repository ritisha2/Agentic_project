"""
Unit Test Suite for Numerical Invariants and RAG Triad Faithfulness
Grounded in Phase 3, Phase 8, and Phase 10 Safety Architecture.
Verifies:
1. Zero-tolerance numerical trip invariants (Motor Temp = 150.0°C, PIP Low = 100.0 psi)
2. Rejection of drifted numbers (140°C, 160°C trigger immediate test failures)
3. Deterministic fallback gate (safety-critical bypass of vector/LLM generation)
4. RAG Triad Faithfulness Claim Verification (Target = 1.0)
"""

import os
import re
import json
import yaml
import pytest

ROOT_DIR = r"x:\TAS\Agentic_project"
ALERTS_FILE = os.path.join(ROOT_DIR, "esp-knowledge", "deterministic", "alerts", "seed_alerts.yaml")
RULES_FILE = os.path.join(ROOT_DIR, "esp_agent", "knowledge_bases", "esp", "rules", "diagnostic_rules.json")


# ==============================================================================
# 1. Deterministic Fallback Gate (No-LLM Bypass) Tests
# ==============================================================================

def test_1_deterministic_gate_loads_safety_critical_thresholds():
    """Verify safety thresholds can be fetched directly from deterministic files without LLM."""
    assert os.path.exists(ALERTS_FILE), f"Missing {ALERTS_FILE}"
    assert os.path.exists(RULES_FILE), f"Missing {RULES_FILE}"

    with open(ALERTS_FILE, "r", encoding="utf-8") as f:
        alerts_data = yaml.safe_load(f)

    with open(RULES_FILE, "r", encoding="utf-8") as f:
        rules_data = json.load(f)

    # Motor Temp Critical Trip
    crit_alert = next((a for a in alerts_data["alerts"] if a["alert_id"] == "MOTOR_TEMP_CRITICAL"), None)
    assert crit_alert is not None, "MOTOR_TEMP_CRITICAL alert missing from deterministic YAML"
    assert crit_alert["trigger"]["threshold"] == 150.0
    assert crit_alert["trigger"]["unit"] == "°C"

    # PIP Low Critical Trip
    crit_pip_rule = next((r for r in rules_data["rules"] if r["rule_id"] == "RULE_PIP_CRIT"), None)
    assert crit_pip_rule is not None, "RULE_PIP_CRIT missing from diagnostic_rules.json"
    assert crit_pip_rule["threshold"] == 100.0
    assert "psi" in crit_pip_rule["description"]

    # BP Playbook: Underload Deadhead Safeguard (80% normal load)
    underload_alert = next((a for a in alerts_data["alerts"] if a["alert_id"] == "ALERT_UNDERLOAD_DEADHEAD_SAFEGUARD"), None)
    assert underload_alert is not None, "ALERT_UNDERLOAD_DEADHEAD_SAFEGUARD missing from deterministic YAML"
    assert underload_alert["trigger"]["threshold"] == 80.0
    assert "burnout" in underload_alert["interpretation"][0]

    # BP Playbook: Upthrust Overload (110% nameplate current)
    overload_alert = next((a for a in alerts_data["alerts"] if a["alert_id"] == "ALERT_UPTHRUST_OVERLOAD_CHOKE_REMEDY"), None)
    assert overload_alert is not None, "ALERT_UPTHRUST_OVERLOAD_CHOKE_REMEDY missing from deterministic YAML"
    assert overload_alert["trigger"]["threshold"] == 110.0
    assert "raise_overload_trip_threshold_above_110" in overload_alert["forbidden_actions"]

    # BP Playbook: Backspin Restart Lockout (1800s / 30min hold)
    backspin_alert = next((a for a in alerts_data["alerts"] if a["alert_id"] == "ALERT_BACKSPIN_TORSION_LOCKOUT"), None)
    assert backspin_alert is not None, "ALERT_BACKSPIN_TORSION_LOCKOUT missing from deterministic YAML"
    assert backspin_alert["trigger"]["threshold"] == 1800.0
    assert "immediate_restart" in backspin_alert["forbidden_actions"]


# ==============================================================================
# 2. Numerical Invariant & Regex Drift Checks
# ==============================================================================

def extract_temperature_limits(advisory_text: str):
    """Regex parser to extract stated temperature trip limits."""
    matches = re.findall(r"(?:motor\s+temp(?:erature)?|trip\s+limit).*?(\d+(?:\.\d+)?)\s*(?:°C|degC|C)", advisory_text, re.IGNORECASE)
    return [float(m) for m in matches]


def extract_pip_limits(advisory_text: str):
    """Regex parser to extract stated PIP low trip limits."""
    matches = re.findall(r"(?:intake\s+pressure|pip\s+low|pip\s+critical).*?(\d+(?:\.\d+)?)\s*(?:psi|bar)", advisory_text, re.IGNORECASE)
    return [float(m) for m in matches]


def test_2_exact_numerical_invariants_enforced():
    """Valid advisory text with exact numbers (150.0 °C and 100.0 psi) must pass."""
    compliant_advisory = (
        "Operating advisory: High thermal alert detected. Per API RP 11S8, the motor temperature "
        "critical trip limit is 150.0 °C. The intake pressure low critical cutoff is 100.0 psi. "
        "Maintain operational clearance immediately."
    )

    temps = extract_temperature_limits(compliant_advisory)
    pips = extract_pip_limits(compliant_advisory)

    assert 150.0 in temps, f"Expected 150.0 °C in extracted temps: {temps}"
    assert 100.0 in pips, f"Expected 100.0 psi in extracted PIPs: {pips}"


def test_3_threshold_drift_detected_and_rejected():
    """Any drifted number (e.g. 140°C or 160°C instead of 150.0°C) must trigger test failure."""
    drifted_advisories = [
        "LLM Advisory: The motor temperature critical trip limit is set to 140 °C per textbook estimate.",
        "LLM Advisory: Motor temperature critical shutdown occurs at 160 °C under heavy load.",
        "LLM Advisory: The PIP low trip point has drifted to 120.0 psi without override."
    ]

    for drifted in drifted_advisories:
        temps = extract_temperature_limits(drifted)
        pips = extract_pip_limits(drifted)

        # Invariant assertion
        drift_detected = False
        for t in temps:
            if t != 150.0:
                drift_detected = True
        for p in pips:
            if p != 100.0:
                drift_detected = True

        assert drift_detected is True, f"Drift was not caught for advisory: {drifted}"


# ==============================================================================
# 3. RAG Triad: Faithfulness Claim Verification
# ==============================================================================

def calculate_faithfulness(advisory_claims: list, source_chunk_text: str) -> float:
    """
    Computes Faithfulness = (Supported Claims) / (Total Claims)
    Target: 1.0 (Zero ungrounded hallucinations)
    """
    if not advisory_claims:
        return 1.0

    chunk_lower = source_chunk_text.lower()
    supported_count = 0

    for claim in advisory_claims:
        # Check claim keywords in source chunk
        keywords = [kw.lower() for kw in claim.split() if len(kw) > 3 and kw.isalnum()]
        match_ratio = sum(1 for kw in keywords if kw in chunk_lower) / max(len(keywords), 1)
        if match_ratio >= 0.75:
            supported_count += 1

    return supported_count / len(advisory_claims)


def test_4_rag_triad_faithfulness_target_one():
    """Grounded advisory achieves 1.0 faithfulness against source chunk."""
    source_chunk = (
        "API RP 11S8 Section 4.2: Maximum allowable motor operating temperature is 150.0 °C. "
        "Intake pressure below 100.0 psi induces severe fluid cavitation and rapid gas locking. "
        "Operators must initiate controlled shutdown if vibration exceeds 5.0 g."
    )

    grounded_claims = [
        "Maximum allowable motor operating temperature is 150.0 °C per API RP 11S8.",
        "Intake pressure below 100.0 psi induces fluid cavitation and gas locking.",
        "Controlled shutdown must be initiated if vibration exceeds 5.0 g."
    ]

    score = calculate_faithfulness(grounded_claims, source_chunk)
    assert score == 1.0, f"Expected 1.0 Faithfulness, got {score}"


def test_5_rag_triad_hallucinated_claim_fails_faithfulness():
    """Ungrounded/hallucinated claim drops Faithfulness below 1.0."""
    source_chunk = (
        "API RP 11S8: Maximum allowable motor temperature is 150.0 °C. "
        "Intake pressure below 100.0 psi induces gas locking."
    )

    hallucinated_claims = [
        "Maximum allowable motor temperature is 150.0 °C.",
        "The system can operate up to 250 °C if synthetic lubricant is injected."  # Hallucinated
    ]

    score = calculate_faithfulness(hallucinated_claims, source_chunk)
    assert score < 1.0, "Hallucinated claim was not penalized in faithfulness calculation"
    assert score == 0.5
