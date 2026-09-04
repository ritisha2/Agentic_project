"""
Unit Test Suite for Pump Curve Catalog and Causal Graph Expansion
Grounded in Phase 3 & BP0757 Engineering Integration.
Verifies:
1. Exact lookup of Alnas 362 S700, M3000, M3800, and Weatherford DN1750 pump curves.
2. Authority level and curve points preservation.
3. GraphAdapter cause-effect tracing for Backspin, Deadhead, and Water Cut failure chains.
"""

import pytest
from src.services.retrieval_service import RetrievalService
from src.adapters.graph import GraphAdapter


@pytest.fixture(scope="module")
def svc():
    return RetrievalService()


# ==============================================================================
# 1. Pump Curve Catalog Tests
# ==============================================================================

def test_1_weatherford_dn1750_pump_curve(svc):
    """Weatherford DN1750 curve lookup with BEP = 1750 BPD."""
    curve = svc.get_pump_curve("Weatherford DN1750")
    assert curve is not None, "Weatherford DN1750 curve missing"
    assert curve["bep_bpd"] == 1750.0
    assert curve["authority_level"] == "B"
    assert len(curve["curve_points"]) >= 5


def test_2_alnas_s700_pump_curve(svc):
    """Alnas 362 S700 curve lookup from BP manual with BEP = 692 BPD (110 m3/d)."""
    curve = svc.get_pump_curve("Alnas 362 S700")
    assert curve is not None, "Alnas 362 S700 curve missing"
    assert curve["bep_bpd"] == 692.0
    assert curve["manufacturer"] == "Alnas"
    assert curve["stage_count"] == 242
    assert curve["authority_level"] == "C"
    assert len(curve["curve_points"]) >= 5


def test_3_alnas_m3000_and_m3800_pump_curves(svc):
    """Alnas 362 M3000 and M3800 curves from BP manual with BEPs = 2768 and 3774 BPD."""
    m3000 = svc.get_pump_curve("Alnas 362 M3000")
    assert m3000 is not None, "Alnas 362 M3000 curve missing"
    assert m3000["bep_bpd"] == 2768.0
    assert m3000["stage_count"] == 166

    m3800 = svc.get_pump_curve("Alnas 362 M3800")
    assert m3800 is not None, "Alnas 362 M3800 curve missing"
    assert m3800["bep_bpd"] == 3774.0
    assert m3800["stage_count"] == 155


# ==============================================================================
# 2. Causal Knowledge Graph Tests
# ==============================================================================

def test_4_graph_topology_contains_bp_failure_modes():
    """Verify esp_graph.json contains BP failure modes and symptoms."""
    adapter = GraphAdapter()
    gdata = adapter._graph_data
    assert len(gdata) > 0, "Graph data failed to load"

    modes = gdata.get("failure_modes", [])
    assert "Spline Shaft Torsion Shear" in modes
    assert "Deadheading Stator Burnout" in modes

    symptoms = gdata.get("symptoms", [])
    assert "Backspin Condition" in symptoms
    assert "Zero Flow Low Current" in symptoms


def test_5_graph_cause_effect_tracing_backspin_and_deadhead():
    """Verify causal tracing from Backspin Condition to Spline Shaft Torsion Shear."""
    adapter = GraphAdapter()

    traces_backspin = adapter.trace_cause_effect("Backspin Condition")
    assert len(traces_backspin) > 0, "No causal trace for Backspin Condition"
    assert any("Spline Shaft Torsion Shear" in t.get("connected_node", "") for t in traces_backspin)

    traces_deadhead = adapter.trace_cause_effect("Zero Flow Low Current")
    assert len(traces_deadhead) > 0, "No causal trace for Zero Flow Low Current"
    assert any("Deadheading Stator Burnout" in t.get("connected_node", "") for t in traces_deadhead)
