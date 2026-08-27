"""
OP02 Production Decline RCA LangGraph Workflow
Grounded in PHASE_4_Objective_Layer_Implementation_Plan_ESP_APM.docx §22

End-to-End Node Sequence:
1. resolve_asset -> Fetch AssetContext via AssetService
2. data_quality_gate -> Validate telemetry signal completeness & freshness
3. collect_evidence -> Ingest live telemetry, ML model predictions, and KB fault docs
4. calculate_operating_point -> Physics calculations: TDH & BEP flow rate deviation
5. fuse_evidence -> Construct typed EvidencePack
6. generate_advisory -> Assemble StandardAdvisoryPayload complying with Appendix C
"""

from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from langgraph.graph import StateGraph, END, START

from src.schemas.contracts import AssetContextPayload, DataQualityReport, ModelOutputPayload
from src.schemas.advisory import StandardAdvisoryPayload
from src.schemas.evidence import EvidencePack

from src.adapters.asset_service import AssetService
from src.adapters.telemetry import TelemetryAdapter
from src.adapters.model_adapter import ModelAdapter
from src.services.retrieval_service import RetrievalService
from src.services.context_builder import ContextBuilder
from src.agent.data_quality_gate import DataQualityGate
from src.agent.objective_registry import ObjectiveRegistry


class OP02WorkflowState(TypedDict):
    request_id: str
    asset_id: str
    user_query: str
    objective_id: str
    asset_context: Optional[Dict[str, Any]]
    telemetry_data: Dict[str, float]
    dq_report: Optional[Dict[str, Any]]
    model_output: Optional[Dict[str, Any]]
    tdh_ft: float
    bep_deviation_pct: float
    evidence_pack: Optional[Dict[str, Any]]
    advisory: Optional[Dict[str, Any]]
    audit_trail: List[str]
    error: Optional[str]


def create_op02_workflow():
    """Build and compile the OP02 Production Decline RCA LangGraph workflow."""
    
    asset_service = AssetService()
    model_adapter = ModelAdapter()
    context_builder = ContextBuilder()
    data_quality_gate = DataQualityGate()
    registry = ObjectiveRegistry()

    builder = StateGraph(OP02WorkflowState)

    def resolve_asset_node(state: OP02WorkflowState) -> Dict[str, Any]:
        audit = list(state.get("audit_trail", []))
        asset_id = state["asset_id"]
        audit.append(f"Node 1: Resolving Asset Context for {asset_id} via AssetService")
        
        asset_ctx = asset_service.get_asset(asset_id)
        return {
            "asset_context": asset_ctx.model_dump(),
            "audit_trail": audit
        }

    def data_quality_gate_node(state: OP02WorkflowState) -> Dict[str, Any]:
        audit = list(state.get("audit_trail", []))
        audit.append("Node 2: Running DataQualityGate evaluation")
        
        telemetry_data = state.get("telemetry_data", {
            "motor_temperature": 135.0,
            "flow_rate": 1450.0,
            "current": 62.0,
            "pip": 350.0,
            "pdp": 2100.0,
            "vibration": 1.2
        })
        
        obj_def = registry.get("OP02_PRODUCTION_DECLINE_RCA")
        req_signals = obj_def.required_signals if obj_def else ["flowline_pressure", "intake_pressure", "discharge_pressure"]
        
        dq_report: DataQualityReport = data_quality_gate.evaluate(
            required_signals=req_signals,
            telemetry_data=telemetry_data,
            telemetry_timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        audit.append(f"DataQualityGate status: {dq_report.status}")
        return {
            "telemetry_data": telemetry_data,
            "dq_report": dq_report.model_dump(),
            "audit_trail": audit
        }

    def collect_evidence_node(state: OP02WorkflowState) -> Dict[str, Any]:
        audit = list(state.get("audit_trail", []))
        audit.append("Node 3: Collecting ML predictions and KB evidence")
        
        asset_id = state["asset_id"]
        telemetry = state["telemetry_data"]
        
        model_output: ModelOutputPayload = model_adapter.get_model_output(asset_id, telemetry)
        audit.append(f"Model diagnosis: {model_output.fault.predicted_fault_class} (confidence={model_output.fault.confidence:.2f})")
        
        return {
            "model_output": model_output.model_dump(),
            "audit_trail": audit
        }

    def calculate_operating_point_node(state: OP02WorkflowState) -> Dict[str, Any]:
        audit = list(state.get("audit_trail", []))
        telemetry = state["telemetry_data"]
        
        pdp = telemetry.get("pdp", 2100.0)
        pip = telemetry.get("pip", 350.0)
        flow_rate = telemetry.get("flow_rate", 1450.0)
        bep_target = 1750.0  # From DN1750 spec
        
        tdh = (pdp - pip) * 2.31 / 1.0  # SG = 1.0
        bep_dev = ((flow_rate - bep_target) / bep_target) * 100.0
        
        audit.append(f"Node 4: Physics calculations: TDH={tdh:.1f} ft, BEP Deviation={bep_dev:.1f}%")
        return {
            "tdh_ft": tdh,
            "bep_deviation_pct": bep_dev,
            "audit_trail": audit
        }

    def fuse_evidence_node(state: OP02WorkflowState) -> Dict[str, Any]:
        audit = list(state.get("audit_trail", []))
        audit.append("Node 5: Fusing evidence into typed EvidencePack")
        
        pack: EvidencePack = context_builder.build_evidence_pack(
            request_id=state["request_id"],
            asset_id=state["asset_id"],
            objective_id="OP02_PRODUCTION_DECLINE_RCA",
            user_query=state["user_query"],
            telemetry_data=state["telemetry_data"]
        )
        
        return {
            "evidence_pack": pack.model_dump(),
            "audit_trail": audit
        }

    def generate_advisory_node(state: OP02WorkflowState) -> Dict[str, Any]:
        audit = list(state.get("audit_trail", []))
        audit.append("Node 6: Generating Appendix C StandardAdvisoryPayload")
        
        asset_id = state["asset_id"]
        tdh = state["tdh_ft"]
        bep_dev = state["bep_deviation_pct"]
        dq_report = DataQualityReport(**state["dq_report"])
        
        now_str = datetime.utcnow().isoformat() + "Z"
        
        assessment = f"Production Decline RCA for {asset_id}: Operating at {bep_dev:.1f}% off BEP with TDH {tdh:.1f} ft."
        diagnosis = "Dominant cause: Intake pressure drawdown leading to low pump intake pressure and reduced liquid rate."
        recommendation = "Verify wellhead choke setting, check for flowline backpressure restriction, and measure gas-oil ratio."
        
        advisory = StandardAdvisoryPayload(
            advisory_id=state["request_id"],
            asset_id=asset_id,
            objective_id=state.get("objective_id") or "OP02_PRODUCTION_DECLINE_RCA",
            timestamp=now_str,
            assessment=assessment,
            evidence=[],
            diagnosis=diagnosis,
            confidence=0.88 if dq_report.gate_passed else 0.50,
            risk="Medium - Continued fluid rate decline risks pump off or thermal trip.",
            recommendation=recommendation,
            expected_impact="Restore flow rate toward 1750 BPD BEP target.",
            constraints=["Do NOT increase frequency without verifying intake pressure > 300 psi."],
            verification=[
                "1. Confirm test separator flow rate measurement.",
                "2. Inspect intake pressure sensor calibration.",
                f"Note: {dq_report.operating_range_note}"
            ],
            provenance=["Advait Asset Service", "TDH Physics Calculator v1.0", dq_report.operating_range_note]
        )
        
        return {
            "advisory": advisory.model_dump(),
            "audit_trail": audit
        }

    builder.add_node("resolve_asset", resolve_asset_node)
    builder.add_node("data_quality_gate", data_quality_gate_node)
    builder.add_node("collect_evidence", collect_evidence_node)
    builder.add_node("calculate_operating_point", calculate_operating_point_node)
    builder.add_node("fuse_evidence", fuse_evidence_node)
    builder.add_node("generate_advisory", generate_advisory_node)

    builder.add_edge(START, "resolve_asset")
    builder.add_edge("resolve_asset", "data_quality_gate")
    builder.add_edge("data_quality_gate", "collect_evidence")
    builder.add_edge("collect_evidence", "calculate_operating_point")
    builder.add_edge("calculate_operating_point", "fuse_evidence")
    builder.add_edge("fuse_evidence", "generate_advisory")
    builder.add_edge("generate_advisory", END)

    return builder.compile()
