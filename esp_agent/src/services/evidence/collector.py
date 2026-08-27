"""
Multi-Source Evidence Collector
Grounded in ESP_APM_PHASE_8_Evidence_Pack_Agent_Context_Implementation_Design.docx §5, §7, §8
"""

import time
import uuid
from typing import List, Dict, Any, Optional
from src.schemas.evidence import (
    EvidenceItem, EvidenceType, AuthorityLevel, QualityStatus
)


class EvidenceCollector:
    """
    Unified collector that ingests raw outputs from upstream services/adapters and
    normalizes them into 22-field canonical EvidenceItem records.
    """

    @classmethod
    def collect_from_asset_context(cls, asset_id: str, context: Dict[str, Any]) -> List[EvidenceItem]:
        items = []
        if not context:
            return items

        pump_model = context.get("pump_model") or "ESP Pump"
        items.append(EvidenceItem(
            evidence_id=f"EVID-AST-{uuid.uuid4().hex[:6]}",
            evidence_type=EvidenceType.ASSET,
            asset_id=asset_id,
            source_system="AssetContextService",
            source_id="installed_pump_model",
            source_version="1.0.0",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            observed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            authority_level=AuthorityLevel.LEVEL_A_INSTALLED_APPROVED,
            quality_status=QualityStatus.GOOD,
            confidence=1.0,
            relevance_score=1.0,
            semantic_type="equipment_spec",
            value=pump_model,
            statement=f"Installed pump model is {pump_model}."
        ))

        motor_hp = context.get("motor_rating_hp")
        if motor_hp:
            items.append(EvidenceItem(
                evidence_id=f"EVID-AST-{uuid.uuid4().hex[:6]}",
                evidence_type=EvidenceType.ASSET,
                asset_id=asset_id,
                source_system="AssetContextService",
                source_id="motor_rating_hp",
                source_version="1.0.0",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                observed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                authority_level=AuthorityLevel.LEVEL_A_INSTALLED_APPROVED,
                quality_status=QualityStatus.GOOD,
                confidence=1.0,
                relevance_score=0.9,
                semantic_type="equipment_spec",
                value=motor_hp,
                unit="hp",
                statement=f"Motor rating is {motor_hp} hp."
            ))

        return items

    @classmethod
    def collect_from_telemetry(cls, asset_id: str, telemetry: Dict[str, float]) -> List[EvidenceItem]:
        items = []
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        for tag, val in telemetry.items():
            unit = "°C" if "temp" in tag else ("psi" if "press" in tag or "pip" in tag or "pdp" in tag else ("amps" if "current" in tag else ("Hz" if "freq" in tag else "bpd")))
            items.append(EvidenceItem(
                evidence_id=f"EVID-TEL-{uuid.uuid4().hex[:6]}",
                evidence_type=EvidenceType.TELEMETRY,
                asset_id=asset_id,
                source_system="TelemetryService",
                source_id=tag,
                source_version="1.0.0",
                timestamp=now_iso,
                observed_at=now_iso,
                authority_level=AuthorityLevel.LEVEL_A_INSTALLED_APPROVED,
                quality_status=QualityStatus.GOOD,
                confidence=1.0,
                relevance_score=0.95,
                semantic_type="sensor_measurement",
                value=val,
                unit=unit,
                statement=f"Telemetry metric '{tag}' measured {val} {unit}."
            ))

        return items

    @classmethod
    def collect_from_engineering(cls, asset_id: str, calculations: Dict[str, Any]) -> List[EvidenceItem]:
        items = []
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        for calc_name, val in calculations.items():
            res_val = val.get("result", val) if isinstance(val, dict) else val
            unit = "ft" if "tdh" in calc_name.lower() else ("%" if "bep" in calc_name.lower() or "deviation" in calc_name.lower() else "psi")
            items.append(EvidenceItem(
                evidence_id=f"EVID-ENG-{uuid.uuid4().hex[:6]}",
                evidence_type=EvidenceType.ENGINEERING,
                asset_id=asset_id,
                source_system="EngineeringService",
                source_id=calc_name,
                source_version="1.0.0",
                timestamp=now_iso,
                observed_at=now_iso,
                authority_level=AuthorityLevel.LEVEL_C_CUSTOMER_ENG,
                quality_status=QualityStatus.GOOD,
                confidence=0.95,
                relevance_score=0.95,
                semantic_type="engineering_calculation",
                value=res_val,
                unit=unit,
                statement=f"Deterministic calculation '{calc_name}' evaluated to {res_val} {unit}."
            ))

        return items

    @classmethod
    def collect_from_models(cls, asset_id: str, models: Dict[str, Any]) -> List[EvidenceItem]:
        items = []
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        for model_name, payload in models.items():
            pred = payload.get("identified_fault") or payload.get("status") or str(payload) if isinstance(payload, dict) else str(payload)
            conf = float(payload.get("confidence", 0.85)) if isinstance(payload, dict) else 0.85

            items.append(EvidenceItem(
                evidence_id=f"EVID-ML-{uuid.uuid4().hex[:6]}",
                evidence_type=EvidenceType.ML,
                asset_id=asset_id,
                source_system="ModelAdapter",
                source_id=model_name,
                source_version="1.0.0",
                timestamp=now_iso,
                observed_at=now_iso,
                authority_level=AuthorityLevel.LEVEL_D_SITE_HISTORY,
                quality_status=QualityStatus.GOOD,
                confidence=conf,
                relevance_score=0.90,
                semantic_type="ml_prediction",
                value=pred,
                statement=f"Predictive model '{model_name}' predicted '{pred}' with confidence {conf:.2f}."
            ))

        return items

    @classmethod
    def collect_from_knowledge(cls, asset_id: str, knowledge_results: List[Dict[str, Any]]) -> List[EvidenceItem]:
        items = []
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        for res in knowledge_results:
            source_title = res.get("source_title") or res.get("source") or "Technical Manual"
            text_claim = res.get("text") or res.get("claim") or ""
            doc_id = res.get("document_id") or "KB-DOC-001"
            page = res.get("page")
            score = float(res.get("similarity") or res.get("score") or 0.85)

            # Determine authority level based on source document title
            auth = AuthorityLevel.LEVEL_B_OEM if ("oem" in source_title.lower() or "weatherford" in source_title.lower() or "baker" in source_title.lower() or "slb" in source_title.lower()) else AuthorityLevel.LEVEL_E_INDUSTRY

            items.append(EvidenceItem(
                evidence_id=f"EVID-KB-{uuid.uuid4().hex[:6]}",
                evidence_type=EvidenceType.KNOWLEDGE,
                asset_id=asset_id,
                source_system="RetrievalService",
                source_id=doc_id,
                source_version="1.0.0",
                timestamp=now_iso,
                observed_at=now_iso,
                authority_level=auth,
                quality_status=QualityStatus.GOOD,
                confidence=score,
                relevance_score=score,
                semantic_type="knowledge_claim",
                value=text_claim[:200],
                statement=f"Retrieved from {source_title} (Page {page or 1}): {text_claim[:150]}...",
                citation=f"{source_title}, DocID: {doc_id}, Page: {page or 1}"
            ))

        return items
