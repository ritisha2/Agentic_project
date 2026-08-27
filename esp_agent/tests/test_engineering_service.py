"""
Tests for ESP Engineering Service & Architecture Integration
Grounded in ESP_APM_Engineering_Service_Architecture_Granular_Design.docx §5, §10, §43
"""

import pytest
from fastapi.testclient import TestClient

from src.schemas.engineering_contracts import (
    CalculationRequest, CalculationBatchRequest, RuntimeData, FluidData,
    ESPEquipmentData, CalculationStatus
)
from src.services.engineering.engine import EngineeringCalculationEngine
from src.api.engineering_service_server import app
from src.agent.specialists.engineering import EngineeringSpecialist
from src.agent.supervisor.specialist_contracts import SpecialistInput


@pytest.fixture
def calc_engine():
    return EngineeringCalculationEngine()


@pytest.fixture
def rest_client():
    return TestClient(app)


def test_1_a1_pressure_to_head_calculation(calc_engine):
    """A1: H = 2.31 * delta_p / SG"""
    req = CalculationRequest(
        calculation_id="A1",
        asset_id="FS-031",
        runtime=RuntimeData(
            intake_pressure_pip_psi=350.0,
            discharge_pressure_pdp_psi=2100.0,
            pressure_diff_psi=1750.0,
            operating_frequency_hz=60.0,
            timestamp="2026-08-27T08:00:00Z"
        ),
        fluid=FluidData(composite_sg=1.0)
    )

    res = calc_engine.execute(req)
    assert res.status == CalculationStatus.SUCCESS
    # 2.31 * 1750 / 1.0 = 4042.5 ft
    assert res.value == 4042.5
    assert res.value_unit == "ft"
    assert res.provenance.calculation_id == "A1"


def test_2_fail_closed_missing_sg(calc_engine):
    """Verify strict fail-closed behavior when Specific Gravity is missing or zero"""
    req = CalculationRequest(
        calculation_id="A1",
        asset_id="FS-031",
        runtime=RuntimeData(
            pressure_diff_psi=1750.0,
            operating_frequency_hz=60.0,
            timestamp="2026-08-27T08:00:00Z"
        ),
        fluid=FluidData(composite_sg=None)
    )

    res = calc_engine.execute(req)
    assert res.status == CalculationStatus.BLOCKED
    assert "fail-closed" in res.block_reason.lower()
    assert res.value is None


def test_3_a2_hydraulic_power_calculation(calc_engine):
    """A2: P_hyd = (Q_gpm * H * SG) / 3960"""
    req = CalculationRequest(
        calculation_id="A2",
        asset_id="FS-031",
        runtime=RuntimeData(
            flow_rate_q_bpd=1450.0,
            operating_frequency_hz=60.0,
            timestamp="2026-08-27T08:00:00Z"
        ),
        overrides={"total_dynamic_head_ft": 4042.5, "composite_sg": 1.0}
    )

    res = calc_engine.execute(req)
    assert res.status == CalculationStatus.SUCCESS
    # (1450 BPD -> 42.2917 GPM * 4042.5 * 1.0) / 3960 = 43.17 hp
    assert round(res.value, 2) == 43.17
    assert res.value_unit == "hp"


def test_4_a4_affinity_laws_frequency_correction(calc_engine):
    """A4: Frequency scaling at 50 Hz vs 60 Hz"""
    req = CalculationRequest(
        calculation_id="A4",
        asset_id="FS-031",
        runtime=RuntimeData(
            flow_rate_q_bpd=1450.0,
            operating_frequency_hz=50.0,
            timestamp="2026-08-27T08:00:00Z"
        ),
        overrides={"total_dynamic_head_ft": 4000.0}
    )

    res = calc_engine.execute(req)
    assert res.status == CalculationStatus.SUCCESS
    # ratio = 50 / 60 = 0.8333
    assert res.value == 0.8333
    assert res.secondary_outputs["adjusted_flow_bpd"] == round(1450 * (50/60), 2)
    assert res.secondary_outputs["adjusted_head_ft"] == round(4000 * ((50/60)**2), 2)


def test_5_a5_bep_percentage_and_c2_motor_load(calc_engine):
    """A5 %BEP and C2 %Motor Load"""
    # A5
    req_a5 = CalculationRequest(
        calculation_id="A5",
        asset_id="FS-031",
        runtime=RuntimeData(flow_rate_q_bpd=1450.0, operating_frequency_hz=60.0, timestamp="2026-08-27T08:00:00Z"),
        equipment=ESPEquipmentData(bep_flow_rate_bpd=1450.0)
    )
    res_a5 = calc_engine.execute(req_a5)
    assert res_a5.status == CalculationStatus.SUCCESS
    assert res_a5.value == 100.0

    # C2
    req_c2 = CalculationRequest(
        calculation_id="C2",
        asset_id="FS-031",
        runtime=RuntimeData(motor_measured_current_a=58.5, operating_frequency_hz=60.0, timestamp="2026-08-27T08:00:00Z"),
        equipment=ESPEquipmentData(motor_nameplate_current_a=65.0)
    )
    res_c2 = calc_engine.execute(req_c2)
    assert res_c2.status == CalculationStatus.SUCCESS
    # (58.5 / 65.0) * 100 = 90.0%
    assert res_c2.value == 90.0


def test_6_b1_oem_pump_curve_interpolation(calc_engine):
    """B1: OEM Pump Curve Interpolation for Baker Hughes D1450"""
    req = CalculationRequest(
        calculation_id="B1",
        asset_id="FS-031",
        runtime=RuntimeData(flow_rate_q_bpd=1450.0, operating_frequency_hz=60.0, timestamp="2026-08-27T08:00:00Z"),
        equipment=ESPEquipmentData(pump_model_id="D1450", stage_count=120)
    )

    res = calc_engine.execute(req)
    assert res.status == CalculationStatus.SUCCESS
    # At 1450 BPD, BEP head per stage is 33.7 ft -> 120 * 33.7 = 4044.0 ft
    assert res.value == 4044.0
    assert res.secondary_outputs["efficiency_pct"] == 74.2


def test_7_e1_ror_range_check(calc_engine):
    """E1: Recommended Operating Range check"""
    req = CalculationRequest(
        calculation_id="E1",
        asset_id="FS-031",
        runtime=RuntimeData(flow_rate_q_bpd=1450.0, operating_frequency_hz=60.0, timestamp="2026-08-27T08:00:00Z"),
        equipment=ESPEquipmentData(pump_model_id="D1450", stage_count=120)
    )

    res = calc_engine.execute(req)
    assert res.status == CalculationStatus.SUCCESS
    assert res.value == 1.0
    assert res.secondary_outputs["ror_status"] == "WITHIN_ROR"


def test_8_engineering_rest_api_server(rest_client):
    """Test REST API endpoints (:8083)"""
    # 1. Health check
    res_h = rest_client.get("/health")
    assert res_h.status_code == 200
    assert res_h.json()["service"] == "esp-engineering-service"

    # 2. Registry list
    res_r = rest_client.get("/api/v1/engineering/registry")
    assert res_r.status_code == 200
    assert res_r.json()["total_calculations"] >= 8

    # 3. Single calculation
    calc_payload = {
        "calculation_id": "A1",
        "asset_id": "FS-031",
        "runtime": {
            "pressure_diff_psi": 1750.0,
            "operating_frequency_hz": 60.0,
            "timestamp": "2026-08-27T08:00:00Z"
        },
        "fluid": {"composite_sg": 1.0}
    }
    res_c = rest_client.post("/api/v1/engineering/calculate", json=calc_payload)
    assert res_c.status_code == 200
    assert res_c.json()["status"] == "SUCCESS"
    assert res_c.json()["value"] == 4042.5

    # 4. Batch calculation
    batch_payload = {
        "asset_id": "FS-031",
        "calculation_ids": ["A1", "A2", "A4", "A5", "C2", "E1"],
        "runtime": {
            "flow_rate_q_bpd": 1450.0,
            "pressure_diff_psi": 1750.0,
            "motor_measured_current_a": 58.5,
            "operating_frequency_hz": 60.0,
            "timestamp": "2026-08-27T08:00:00Z"
        },
        "fluid": {"composite_sg": 1.0},
        "equipment": {"pump_model_id": "D1450", "stage_count": 120, "motor_nameplate_current_a": 65.0, "bep_flow_rate_bpd": 1450.0}
    }
    res_b = rest_client.post("/api/v1/engineering/batch", json=batch_payload)
    assert res_b.status_code == 200
    assert res_b.json()["status"] == "COMPLETED"
    assert len(res_b.json()["results"]) == 6


def test_9_engineering_specialist_langgraph_integration():
    """Test EngineeringSpecialist LangGraph subgraph execution"""
    specialist = EngineeringSpecialist()

    inp = SpecialistInput(
        run_id="RUN-ENG-TEST-001",
        objective_id="OBJ-TEST-ENG",
        asset_id="FS-031",
        task="Evaluate hydraulic head and motor load",
        policy_context={
            "telemetry": {
                "flow_rate": 1450.0,
                "pip": 350.0,
                "pdp": 2100.0,
                "frequency": 60.0,
                "motor_current": 58.5,
                "motor_temperature": 110.0,
                "timestamp": "2026-08-27T08:00:00Z"
            }
        }
    )

    output = specialist.run(inp)
    assert output.specialist_id == "EngineeringSpecialist"
    assert output.status == "complete"
    assert len(output.findings) >= 4
    assert any("Total Dynamic Head" in f for f in output.findings)
    assert any("Hydraulic Power" in f for f in output.findings)
    assert len(output.evidence_refs) >= 8
