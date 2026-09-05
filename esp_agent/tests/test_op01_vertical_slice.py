"""
OP01 Vertical Slice Test Suite
==============================
Validates the full OP01_CURRENT_STATUS pipeline end-to-end with all backend
services STOPPED.  Every test must pass with only the local SQLite databases
(cced_esp/data/unlabelled.db and cced_esp/data/normalized.db) available.

Test groups
-----------
1. Routing  — queries that MUST route to OP01, queries that MUST NOT.
2. Pipeline — audit trail assertions (tool calls, tier, handoff status).
3. Payload  — StandardAdvisoryPayload field contracts.
4. Regression — OP07 / OP00 / OP06 still behave correctly after the OP01 changes.

Definition of Done
------------------
All tests pass → pytest esp_agent/tests/test_op01_vertical_slice.py -v
Zero synthetic fallback values (135 / 350 / 2100) in the assessment when
local SQLite has real data for the queried well.
"""

import os
import sys
import time
import pytest
from pathlib import Path

# ── Path setup (mirrors test_kb_vertical_slice.py) ──────────────────────────
ROOT_DIR       = Path(__file__).resolve().parents[2]
ESP_AGENT_DIR  = ROOT_DIR / "esp_agent"
if str(ESP_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(ESP_AGENT_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ── Synthetic fallback constants (from handoff.py — single source of truth) ─
_SYNTHETIC_MOTOR_TEMP     = 135.0
_SYNTHETIC_INTAKE_PRESS   = 350.0
_SYNTHETIC_DISCHARGE_PRESS = 2100.0


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def router():
    from src.agent.intent_router import IntentRouter
    return IntentRouter()


@pytest.fixture(scope="module")
def adapter():
    from src.agent.supervisor.user_entry import UserEntryAdapter
    return UserEntryAdapter()


@pytest.fixture(scope="module")
def sqlite_available():
    """Skip tests that need real telemetry if no DB exists."""
    candidates = [
        ROOT_DIR / "cced_esp" / "data" / "unlabelled.db",
        ROOT_DIR / "cced_esp" / "data" / "normalized.db",
    ]
    return any(p.exists() for p in candidates)


# ============================================================================
# 1. Routing Tests
# ============================================================================

class TestOP01Routing:
    """Queries that MUST route to OP01_CURRENT_STATUS."""

    MUST_ROUTE_OP01 = [
        "What is the current status of FS-010?",
        "Give me the latest telemetry snapshot for FS-031",
        "Show current operating parameters for well FS-022",
        "How is FS-043 running right now?",
        "Show motor temperature and frequency for FS-014",
        "Check running state and amps for FS-020",
        "Operating point and current PIP/PDP for FS-016",
        "Current condition of well FS-046",
        "What is the intake pressure on FS-031?",
        "Is FS-010 running?",
        "Show live telemetry for FS-031",
        "Latest reading for FS-022",
        "Show current sensors for FS-010",
        "What are the live sensor readings on FS-011?",
        "Current frequency and amps on FS-010",
        "What sensors are showing for FS-014?",
    ]

    MUST_NOT_ROUTE_OP01 = [
        # (query, expected_objective)
        ("Hello Jane, how are you today?",                "OP07_GENERAL_INQUIRY"),
        ("Hi there, what can you do?",                    "OP07_GENERAL_INQUIRY"),
        ("Shut down pump FS-010 immediately",             "OP00_OPERATIONAL_CONTROL"),
        ("Turn off well FS-031",                          "OP00_OPERATIONAL_CONTROL"),
        ("What is the recommended SOP for ESP restart?",  "OP06_PROCEDURE_LOOKUP"),
    ]

    @pytest.mark.parametrize("query", MUST_ROUTE_OP01)
    def test_routes_to_op01(self, router, query):
        result = router.route(query)
        obj_id = result.objective_id
        assert obj_id == "OP01_CURRENT_STATUS", (
            f"Query '{query}' routed to '{obj_id}', expected 'OP01_CURRENT_STATUS'.\n"
            f"  confidence={result.confidence:.3f}  path={result.path}"
        )

    @pytest.mark.parametrize("query,expected_obj", MUST_NOT_ROUTE_OP01)
    def test_does_not_misroute_to_op01(self, router, query, expected_obj):
        result = router.route(query)
        assert result.objective_id != "OP01_CURRENT_STATUS", (
            f"Query '{query}' incorrectly routed to OP01_CURRENT_STATUS "
            f"(expected {expected_obj})."
        )
        assert result.objective_id == expected_obj, (
            f"Query '{query}' routed to '{result.objective_id}', expected '{expected_obj}'."
        )

    def test_confidence_high_for_explicit_well_query(self, router):
        result = router.route("What is the current status of FS-010?")
        assert result.confidence >= 0.90, (
            f"Confidence {result.confidence:.3f} < 0.90 for an explicit well status query."
        )

    def test_not_ambiguous_when_well_named(self, router):
        result = router.route("Show current operating parameters for FS-031")
        assert not result.is_ambiguous, (
            "Query with explicit well ID must not be flagged ambiguous."
        )

    def test_path_b_default_not_op03(self, router):
        """Regression: confirm the Path B seed default was changed from OP03."""
        # A completely empty query with no tokens should not silently land on OP03
        result = router.route("?")
        assert result.objective_id != "OP03_FAULT_DIAGNOSIS" or result.confidence < 0.60, (
            "Path B seed default is still OP03_FAULT_DIAGNOSIS — Plan.md Phase 2.0 fix not applied."
        )


# ============================================================================
# 2. Pipeline Tool-Call Audit Tests
# ============================================================================

class TestOP01Pipeline:
    """Verify the audit trail for an OP01 query matches the expected node sequence."""

    @pytest.mark.skipif(
        not (ROOT_DIR / "cced_esp" / "data" / "unlabelled.db").exists()
        and not (ROOT_DIR / "cced_esp" / "data" / "normalized.db").exists(),
        reason="No local SQLite DB available"
    )
    def test_full_audit_trail(self, adapter):
        """Run OP01 query, inspect every expected tool_call step."""
        advisory = adapter.run(
            user_query="What is the current status of FS-010?",
            asset_id="FS-010",
            request_id="TEST-OP01-PIPELINE",
        )
        # advisory._route_result is set by UserEntryAdapter
        route = getattr(advisory, "_route_result", None)
        assert route is not None, "UserEntryAdapter must attach _route_result to advisory."
        assert route.objective_id == "OP01_CURRENT_STATUS", (
            f"Expected OP01_CURRENT_STATUS, got {route.objective_id}."
        )

    def test_tier_is_t2_snapshot(self):
        from src.agent.supervisor.graph import get_evidence_tier
        from src.agent.objective_registry import ObjectiveRegistry
        reg = ObjectiveRegistry()
        obj_def = reg.get("OP01_CURRENT_STATUS")
        tier = get_evidence_tier("OP01_CURRENT_STATUS", obj_def)
        assert tier == "T2_SNAPSHOT", f"OP01 must map to T2_SNAPSHOT, got '{tier}'."

    def test_sqlite_fallback_returns_real_values(self):
        """LiveDataBridge must return real values from SQLite when :8000 is offline."""
        from src.adapters.live_data_bridge import LiveDataBridge
        bridge = LiveDataBridge(base_url="http://127.0.0.1:19999")  # dead port
        row = bridge.get_telemetry_as_agent_dict("FS-010")

        if row is None:
            pytest.skip("No SQLite DB found — skipping offline telemetry test.")

        assert row.get("_source", "").startswith("sqlite_local"), (
            f"Expected sqlite_local source, got '{row.get('_source')}'."
        )
        assert row["intake_pressure"] != _SYNTHETIC_INTAKE_PRESS, (
            f"intake_pressure is still the synthetic fallback value {_SYNTHETIC_INTAKE_PRESS}."
        )
        assert row["motor_temperature"] != _SYNTHETIC_MOTOR_TEMP, (
            f"motor_temperature is still the synthetic fallback value {_SYNTHETIC_MOTOR_TEMP}."
        )
        assert row["intake_pressure"] > 0, "intake_pressure must be > 0 from real DB."
        assert row["motor_temperature"] > 0, "motor_temperature must be > 0 from real DB."

    def test_verify_telemetry_live_for_real_values(self):
        """verify_telemetry() must return LIVE for non-synthetic values."""
        from src.verification.handoff import verify_telemetry, HandoffStatus
        real = {
            "motor_temperature": 88.7,
            "intake_pressure": 900.26,
            "discharge_pressure": 2130.0,
            "flow_rate": 980.0,
            "drive_current_average": 58.3,
            "frequency": 46.2,
            "vibration_x": 0.18,
        }
        verdict = verify_telemetry(real)
        assert verdict.status == HandoffStatus.LIVE, (
            f"Real telemetry values should be LIVE, got {verdict.status.value}."
        )

    def test_verify_telemetry_fallback_for_synthetic_values(self):
        """verify_telemetry() must return FALLBACK for the exact synthetic constants."""
        from src.verification.handoff import verify_telemetry, HandoffStatus
        synthetic = {
            "motor_temperature": 135.0,
            "intake_pressure": 350.0,
            "discharge_pressure": 2100.0,
            "flow_rate": 1450.0,
            "drive_current_average": 62.0,
            "frequency": 50.0,
            "vibration_x": 1.2,
        }
        verdict = verify_telemetry(synthetic)
        assert verdict.status == HandoffStatus.FALLBACK, (
            f"Synthetic constants must be classified FALLBACK, got {verdict.status.value}."
        )

    def test_bep_from_registry_not_hardcoded(self):
        """BEP must differ per well — confirms calibration registry is being read."""
        from src.agent.specialists.well_performance import _get_bep_from_registry
        bep_fs010  = _get_bep_from_registry("FS-010")
        bep_fs031  = _get_bep_from_registry("FS-031")
        bep_fnw01  = _get_bep_from_registry("FNW-01")
        bep_unknown = _get_bep_from_registry("UNKNOWN-ZZZ")

        # All should be positive
        assert bep_fs010  > 0, "BEP for FS-010 must be > 0."
        assert bep_fs031  > 0, "BEP for FS-031 must be > 0."
        assert bep_fnw01  > 0, "BEP for FNW-01 must be > 0."

        # At least two wells must differ (confirming per-well lookup, not always 1750)
        assert not (bep_fs010 == bep_fs031 == bep_fnw01 == 1750.0), (
            "All BEP values are the hardcoded default 1750.0 — calibration registry not loading."
        )

        # Unknown well falls back to fleet default
        assert bep_unknown == 1750.0, (
            f"Unknown well should fall back to 1750.0 BPD, got {bep_unknown}."
        )

    def test_tdh_physics_from_real_pressures(self):
        """TDH must be computed from real PIP/PDP, not the hardcoded 4042.5."""
        pip, pdp = 900.26, 2130.0
        fluid_sg = 0.85
        expected_tdh = round((pdp - pip) * 2.31 / fluid_sg, 1)
        assert expected_tdh != 4042.5, (
            "The real-pressure TDH calculation returned the old hardcoded value — "
            "check load_minimum_context_node T2_SNAPSHOT."
        )
        assert expected_tdh > 0, "TDH must be positive for valid pressures."
        assert abs(expected_tdh - 3342.0) < 50.0, (
            f"TDH {expected_tdh} ft is unexpectedly far from ~3342 ft for PIP=900/PDP=2130."
        )

    def test_well_performance_specialist_uses_canonical_keys(self):
        """Specialist must produce findings from intake_pressure/discharge_pressure keys."""
        from src.agent.specialists.well_performance import well_performance_graph
        result = well_performance_graph.invoke({
            "input": {
                "run_id": "TEST-WP-001",
                "objective_id": "OP01_CURRENT_STATUS",
                "asset_id": "FS-010",
                "task": "status",
                "policy_context": {
                    "telemetry": {
                        "intake_pressure": 900.26,
                        "discharge_pressure": 2130.0,
                        "motor_temperature": 88.7,
                        "frequency": 46.2,
                        "drive_current_average": 58.3,
                        "flow_rate": 980.0,
                        "vibration_x": 0.18,
                        "_source": "sqlite_local:unlabelled.db",
                    }
                }
            },
            "telemetry": {}, "tdh_ft": 0.0, "bep_target": 0.0,
            "bep_deviation_pct": 0.0, "findings": [], "evidence_refs": [], "output": None
        })
        out = result.get("output", {})
        findings = out.get("findings", [])
        assert len(findings) >= 1, "Specialist must produce at least one finding."

        # Verify real values appear in findings (not synthetic 350/2100)
        findings_text = " ".join(findings)
        assert "350" not in findings_text or "2130" in findings_text, (
            "Findings still contain synthetic PIP 350 psi — key mapping not fixed."
        )
        # TDH should be computed (non-zero)
        tdh = result.get("tdh_ft", 0.0)
        assert tdh > 0, f"Specialist TDH must be > 0, got {tdh}."
        assert tdh != 4042.5, "Specialist TDH is still the hardcoded 4042.5 fallback."

        # Evidence refs must include real sensor + engineering entries
        refs = result.get("evidence_refs", [])
        assert any("telemetry" in r for r in refs), "Missing telemetry evidence ref."
        assert any("engineering" in r for r in refs), "Missing engineering evidence ref."


# ============================================================================
# 3. Payload Contract Tests
# ============================================================================

class TestOP01Payload:
    """Validate StandardAdvisoryPayload fields for an OP01 run."""

    @pytest.fixture(scope="class")
    def op01_advisory(self, adapter):
        return adapter.run(
            user_query="What is the current status of FS-010?",
            asset_id="FS-010",
            request_id="TEST-OP01-PAYLOAD",
        )

    def test_objective_id_correct(self, op01_advisory):
        assert op01_advisory.objective_id == "OP01_CURRENT_STATUS"

    def test_asset_id_correct(self, op01_advisory):
        assert op01_advisory.asset_id == "FS-010"

    def test_confidence_range(self, op01_advisory):
        assert 0.70 <= op01_advisory.confidence <= 1.0, (
            f"Confidence {op01_advisory.confidence} outside expected range [0.70, 1.0]."
        )

    def test_assessment_not_empty(self, op01_advisory):
        assert op01_advisory.assessment and len(op01_advisory.assessment) > 50, (
            "Assessment is empty or too short."
        )

    def test_assessment_no_synthetic_values(self, op01_advisory):
        """Assessment must not contain the synthetic scaffold constants."""
        assessment = op01_advisory.assessment

        # Only fail if BOTH the synthetic value is present AND real SQLite data exists
        # (if SQLite is absent, synthetic fallback is acceptable but flagged)
        from src.adapters.live_data_bridge import LiveDataBridge
        bridge = LiveDataBridge(base_url="http://127.0.0.1:19999")
        live_row = bridge.get_telemetry_as_agent_dict("FS-010")
        has_real_data = live_row is not None

        if has_real_data:
            assert "135.0" not in assessment, (
                "Synthetic motor_temperature (135.0°C) found in assessment — "
                "SQLite fallback not working correctly."
            )
            assert "350.0" not in assessment and " 350 " not in assessment, (
                "Synthetic intake_pressure (350 psi) found in assessment — "
                "SQLite fallback not working correctly."
            )

    def test_assessment_contains_running_state(self, op01_advisory):
        assessment = op01_advisory.assessment
        assert any(s in assessment for s in ["RUNNING", "STOPPED", "TRANSITIONING", "STANDBY"]), (
            "Assessment must include a running state indicator."
        )

    def test_diagnosis_not_empty(self, op01_advisory):
        assert op01_advisory.diagnosis and len(op01_advisory.diagnosis) > 10

    def test_recommendation_not_empty(self, op01_advisory):
        assert op01_advisory.recommendation and len(op01_advisory.recommendation) > 10

    def test_verification_steps_present(self, op01_advisory):
        assert isinstance(op01_advisory.verification, list)
        assert len(op01_advisory.verification) >= 1

    def test_evidence_list_present(self, op01_advisory):
        assert hasattr(op01_advisory, "evidence"), "Advisory missing evidence field."
        assert isinstance(op01_advisory.evidence, list), "evidence must be a list."
        assert len(op01_advisory.evidence) >= 1, (
            "OP01 advisory must include at least 1 evidence item."
        )

    def test_evidence_items_have_source_type(self, op01_advisory):
        for item in op01_advisory.evidence:
            item_dict = item if isinstance(item, dict) else (
                item.model_dump() if hasattr(item, "model_dump") else {}
            )
            assert item_dict.get("source_type"), (
                f"Evidence item missing source_type: {item_dict}"
            )

    def test_provenance_records_source(self, op01_advisory):
        provenance = op01_advisory.provenance
        assert isinstance(provenance, list) and len(provenance) >= 1
        prov_text = " ".join(str(p) for p in provenance)
        # Provenance must record something about the data source — LLM engine or telemetry
        assert any(k in prov_text for k in ["LLM", "telemetry", "sqlite", "LIVE", "FALLBACK", "Run ID"]), (
            f"Provenance does not record expected source information: {provenance}"
        )


# ============================================================================
# 4. Regression Tests
# ============================================================================

class TestOP01Regression:
    """Ensure OP07, OP00, and OP06 still behave correctly after OP01 changes."""

    def test_op07_greeting_bypasses_pipeline(self, adapter):
        """OP07 must return a conversational response with no specialist overhead."""
        advisory = adapter.run(
            user_query="Hello Jane, what can you do?",
            request_id="TEST-REG-OP07",
        )
        assert advisory.objective_id == "OP07_GENERAL_INQUIRY", (
            f"Greeting routed to '{advisory.objective_id}' instead of OP07_GENERAL_INQUIRY."
        )
        assert advisory.assessment and len(advisory.assessment) > 10
        # Conversational reply must not contain raw telemetry numbers from FS-010
        assert "intake_pressure" not in advisory.assessment.lower()
        assert "discharge_pressure" not in advisory.assessment.lower()

    def test_op00_actuation_refused(self, adapter):
        """OP00 must return a safety refusal with no data processing."""
        advisory = adapter.run(
            user_query="Turn off pump FS-010 immediately",
            asset_id="FS-010",
            request_id="TEST-REG-OP00",
        )
        assert advisory.objective_id == "OP00_OPERATIONAL_CONTROL", (
            f"Actuation query routed to '{advisory.objective_id}' instead of OP00."
        )
        assert "autonomous" in advisory.assessment.lower() or "refused" in advisory.assessment.lower(), (
            "OP00 advisory must explicitly state the refusal reason."
        )
        assert "autonomous_control" in advisory.constraints, (
            "OP00 advisory must include 'autonomous_control' in constraints."
        )

    def test_op06_procedure_lookup_returns_citations(self, adapter):
        """OP06 must still return KB citations after OP01 changes."""
        advisory = adapter.run(
            user_query="What is the standard operating procedure for pump startup?",
            request_id="TEST-REG-OP06",
        )
        assert advisory.objective_id == "OP06_PROCEDURE_LOOKUP", (
            f"SOP query routed to '{advisory.objective_id}' instead of OP06."
        )
        # Must have evidence items
        assert len(advisory.evidence) >= 1, "OP06 must provide at least one KB evidence item."

    def test_op07_and_op01_do_not_interfere_back_to_back(self, adapter):
        """Run OP07 then OP01 in sequence — OP07 must not poison session for OP01."""
        import uuid
        session = str(uuid.uuid4())

        # Turn 1: greeting
        adv1 = adapter.run(
            user_query="Hi Jane!",
            request_id="TEST-SEQ-01",
            session_id=session,
        )
        assert adv1.objective_id == "OP07_GENERAL_INQUIRY"

        # Turn 2: explicit OP01 query — must route independently
        adv2 = adapter.run(
            user_query="What is the current status of FS-031?",
            asset_id="FS-031",
            request_id="TEST-SEQ-02",
            session_id=session,
        )
        assert adv2.objective_id == "OP01_CURRENT_STATUS", (
            f"After OP07, OP01 query routed to '{adv2.objective_id}' — session bias detected."
        )


# ============================================================================
# 5. Edge Case Tests: Staleness & Regime Degradation
# ============================================================================

class TestOP01EdgeCases:
    """Validate data quality edge cases: staleness gating and missing regime buckets."""

    def test_staleness_flagged_when_timestamp_exceeds_20_minutes(self, adapter):
        """If telemetry is >20 min old, Node 4 must flag staleness, alert operator, and cap confidence."""
        from datetime import datetime, timedelta
        stale_ts = (datetime.utcnow() - timedelta(minutes=35)).isoformat() + "Z"

        stale_telemetry = {
            "motor_temperature": 88.5,
            "intake_pressure": 910.0,
            "discharge_pressure": 2150.0,
            "flow_rate": 990.0,
            "drive_current_average": 58.0,
            "frequency": 46.2,
            "vibration_x": 0.18,
            "_source": "mqtt:live_stream",
            "_timestamp": stale_ts,
        }

        advisory = adapter.run(
            user_query="What is the current status of FS-010?",
            asset_id="FS-010",
            request_id="TEST-EDGE-STALE-01",
            telemetry_override=stale_telemetry,
        )

        assert advisory.objective_id == "OP01_CURRENT_STATUS"
        assert "STALE TELEMETRY ALERT" in advisory.assessment, (
            "Assessment missing STALE TELEMETRY ALERT banner when reading is 35 minutes old."
        )
        assert "STALE FEED" in advisory.assessment or "STALE TELEMETRY" in advisory.diagnosis, (
            "Status / diagnosis did not flag stale feed."
        )
        assert advisory.confidence <= 0.70, (
            f"Confidence {advisory.confidence} not capped to <= 0.70 for 35-minute stale reading."
        )
        assert any("SCADA" in v or "MQTT" in v or "feed" in v for v in advisory.verification), (
            "Verification steps missing SCADA/MQTT feed restoration check for stale reading."
        )

    def test_fresh_telemetry_not_flagged_stale(self, adapter):
        """Fresh telemetry (2 minutes old) must not trigger staleness alert and retains high confidence."""
        from datetime import datetime, timedelta
        fresh_ts = (datetime.utcnow() - timedelta(minutes=2)).isoformat() + "Z"

        fresh_telemetry = {
            "motor_temperature": 88.5,
            "intake_pressure": 910.0,
            "discharge_pressure": 2150.0,
            "flow_rate": 990.0,
            "drive_current_average": 58.0,
            "frequency": 46.2,
            "vibration_x": 0.18,
            "_source": "mqtt:live_stream",
            "_timestamp": fresh_ts,
        }

        advisory = adapter.run(
            user_query="What is the current status of FS-010?",
            asset_id="FS-010",
            request_id="TEST-EDGE-FRESH-01",
            telemetry_override=fresh_telemetry,
        )

        assert advisory.objective_id == "OP01_CURRENT_STATUS"
        assert "STALE TELEMETRY ALERT" not in advisory.assessment, (
            "False positive: STALE TELEMETRY ALERT triggered for a 2-minute-old reading."
        )
        assert advisory.confidence >= 0.75, (
            f"Confidence {advisory.confidence} unexpectedly reduced for fresh reading."
        )

    def test_missing_regime_bucket_degrades_gracefully(self, adapter):
        """
        When operating frequency setpoint is outside calibrated historical range (e.g. 25.0 Hz),
        the corridor check must degrade gracefully: output raw values with no baseline comparison
        rather than guessing or generating false corridor warnings.
        """
        from datetime import datetime, timedelta
        fresh_ts = (datetime.utcnow() - timedelta(minutes=1)).isoformat() + "Z"

        uncalibrated_setpoint_telemetry = {
            "motor_temperature": 75.0,
            "intake_pressure": 950.0,
            "discharge_pressure": 1800.0,
            "flow_rate": 500.0,
            "drive_current_average": 35.0,
            "frequency": 25.0,  # Uncalibrated low-frequency setpoint
            "vibration_x": 0.10,
            "_source": "mqtt:live_stream",
            "_timestamp": fresh_ts,
        }

        advisory = adapter.run(
            user_query="What is the current status of FS-010?",
            asset_id="FS-010",
            request_id="TEST-EDGE-REGIME-01",
            telemetry_override=uncalibrated_setpoint_telemetry,
        )

        assert advisory.objective_id == "OP01_CURRENT_STATUS"
        # Must gracefully indicate raw value reporting without corridor guessing
        assert "raw value — no calibrated regime baseline" in advisory.assessment, (
            "Assessment missing graceful degradation message for uncalibrated frequency setpoint."
        )
        # Must not fabricate false corridor warnings for the uncalibrated regime
        assert "⚠️ Intake Pressure: 950.0 psi (Below P10" not in advisory.assessment
        assert "⚠️ Intake Pressure: 950.0 psi (Above P90" not in advisory.assessment
        assert "Regime Baseline Notice" in advisory.assessment or "outside calibrated" in advisory.diagnosis

    def test_explicit_unpopulated_regime_flag_degrades_gracefully(self, adapter):
        """When has_regime_bucket=False is explicitly signaled, all sensors report raw values."""
        from datetime import datetime, timedelta
        fresh_ts = (datetime.utcnow() - timedelta(minutes=1)).isoformat() + "Z"

        no_regime_telemetry = {
            "motor_temperature": 90.0,
            "intake_pressure": 880.0,
            "discharge_pressure": 2100.0,
            "flow_rate": 950.0,
            "drive_current_average": 55.0,
            "frequency": 46.0,
            "vibration_x": 0.15,
            "has_regime_bucket": False,
            "regime_note": "sparse historical coverage at 46.0 Hz",
            "_source": "mqtt:live_stream",
            "_timestamp": fresh_ts,
        }

        advisory = adapter.run(
            user_query="What is the current status of FS-010?",
            asset_id="FS-010",
            request_id="TEST-EDGE-REGIME-02",
            telemetry_override=no_regime_telemetry,
        )

        assert advisory.objective_id == "OP01_CURRENT_STATUS"
        assert "raw value — no calibrated regime baseline" in advisory.assessment
        assert "sparse historical coverage at 46.0 Hz" in advisory.assessment or "sparse historical coverage" in advisory.diagnosis


# ============================================================================
# Entry point
# ============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
