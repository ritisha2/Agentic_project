"""
Test Suite: KB Multi-Modal Response Cards Verification
Validates:
- ProcedureKnowledgeService returns structured fields (thresholds_table, execution_steps, prohibited_actions, citations)
- Backspin & Startup SOP scenarios
- format_kb_modal_response() generates all 5 card sections correctly
- Evidence items are grounded citations only (no fabricated claims)
"""

import pytest
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
ESP_AGENT_DIR = ROOT_DIR / "esp_agent"
if str(ESP_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(ESP_AGENT_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def test_startup_sop_structured_payload():
    """Verify startup procedure returns structured checklists and citations."""
    from src.services.procedure_knowledge import procedure_knowledge_service

    res = procedure_knowledge_service.format_advisory_text("What is the startup procedure for ESP FS-031?", "FS-031")
    assert "assessment" in res
    assert "thresholds_table" in res
    assert len(res["thresholds_table"]) > 0
    assert "execution_steps" in res
    assert len(res["execution_steps"]) >= 2
    assert "prohibited_actions" in res
    assert any("NEVER" in a for a in res["prohibited_actions"])
    assert "citations" in res
    assert len(res["citations"]) > 0
    assert res["citations"][0]["authority_level"] == "A"


def test_backspin_sop_structured_payload():
    """Verify backspin inquiry returns safety lockout and reverse rotation rules."""
    from src.services.procedure_knowledge import procedure_knowledge_service

    res = procedure_knowledge_service.format_advisory_text("What is the procedure for backspin?", "FS-031")
    assert "Backspin" in res["governing_standard"]
    assert any("spline shaft" in a.lower() for a in res["prohibited_actions"])
    assert len(res["thresholds_table"]) > 0
    # Citations must cite API RP 11S / OEM
    assert any("API" in c["document_id"] for c in res["citations"])


def test_operating_limits_structured_payload():
    """Verify temperature and PIP limits return formatted thresholds table."""
    from src.services.procedure_knowledge import procedure_knowledge_service

    res = procedure_knowledge_service.format_advisory_text("What are the motor temperature tripping limits?", "FS-031")
    assert len(res["thresholds_table"]) > 0
    t_names = [t["parameter"] for t in res["thresholds_table"]]
    assert any("Temperature" in n for n in t_names)


def test_format_kb_modal_response_html():
    """Verify format_kb_modal_response renders all 5 card sections into clean HTML."""
    from agent_streamlit import format_kb_modal_response
    from src.schemas.advisory import StandardAdvisoryPayload, AdvisoryEvidenceItem

    evidence = [
        AdvisoryEvidenceItem(
            source_type="Knowledge Base",
            source_id="esp:kb:API_RP_11S:Section 6: Startup",
            observation="Knowledge Base: API_RP_11S §Section 6: Startup & Commissioning",
            timestamp="2026-09-04T12:00:00Z",
            source_deep_link="http://localhost:6333/dashboard#/collections/esp_kb"
        )
    ]
    thresholds = [
        {"parameter": "Motor Temp", "normal": "< 125°C", "warning": "130°C", "trip": "150°C", "action": "Trip relay"}
    ]
    adv = StandardAdvisoryPayload(
        advisory_id="ADV-TEST-001",
        asset_id="FS-031",
        objective_id="OP06_PROCEDURE_LOOKUP",
        timestamp="2026-09-04T12:00:00Z",
        assessment="Standard ESP startup sequence per API RP 11S.",
        evidence=evidence,
        diagnosis="API RP 11S Startup procedure",
        confidence=0.98,
        risk="Low",
        recommendation="Follow pre-start checklist.",
        expected_impact="Smooth commissioning",
        constraints=["CRITICAL: NEVER start during backspin rotation."],
        verification=["1. Megger test motor cable.", "2. Confirm flowline valves open."],
        provenance=["API RP 11S Section 6 (Authority Level A)"],
        expected_vs_actual=thresholds
    )

    html = format_kb_modal_response(adv, "FS-031")
    
    # Assert all 5 core card components exist in the HTML output
    assert "kb-standard-banner" in html
    assert "Operational Thresholds &amp; Protective Limits" in html
    assert "corridor-table" in html
    assert "Motor Temp" in html
    assert "kb-prohibited-alert" in html
    assert "NEVER start during backspin rotation" in html
    assert "Operator Verification Protocol" in html
    assert "Megger test motor cable" in html
    assert "Authoritative Evidence &amp; Standard Citations" in html
    assert "API_RP_11S" in html
    assert "http://localhost:6333" in html
