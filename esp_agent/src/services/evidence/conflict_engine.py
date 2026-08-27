"""
Conflict Engine for Multi-Source Evidence
Grounded in ESP_APM_PHASE_8_Evidence_Pack_Agent_Context_Implementation_Design.docx §13
"""

import uuid
from typing import List, Dict, Any, Optional
from src.schemas.evidence import EvidenceItem, EvidenceConflict, EvidenceType, AuthorityLevel


class ConflictEngine:
    """
    Detects and constructs explicit EvidenceConflict records when contradictory sources disagree.
    """

    @classmethod
    def detect_conflicts(cls, items: List[EvidenceItem]) -> List[EvidenceConflict]:
        """
        Scans evidence items for ML vs. Physics engineering or multi-sensor discrepancies.
        """
        conflicts: List[EvidenceConflict] = []

        # 1. Check ML Models vs. Engineering Physics Calculations
        ml_items = [i for i in items if i.evidence_type == EvidenceType.ML]
        eng_items = [i for i in items if i.evidence_type == EvidenceType.ENGINEERING]

        for ml in ml_items:
            for eng in eng_items:
                # Example: ML claims Gas Interference but Engineering TDH shows Normal Hydraulic head
                ml_val = str(ml.value).lower()
                eng_val = str(eng.value).lower()
                if ("gas" in ml_val and "normal" in eng_val) or ("anomalous" in ml_val and "stable" in eng_val):
                    conflicts.append(EvidenceConflict(
                        conflict_id=f"CONF-ML-ENG-{uuid.uuid4().hex[:6]}",
                        evidence_refs=[ml.evidence_id, eng.evidence_id],
                        conflict_type="ML_VS_PHYSICS",
                        values={ml.source_id: ml.value, eng.source_id: eng.value},
                        authority_comparison=f"Deterministic Calculation ({eng.authority_level.value}) > ML Model ({ml.authority_level.value})",
                        impact="HIGH",
                        resolution_status="SURFACED",
                        resolution_method="Deterministic engineering physics calculation maintained as authoritative baseline; ML prediction retained as secondary anomaly flag.",
                        next_verification=["1. Inspect wellhead physical pressure gauge.", "2. Perform acoustic fluid level measurement."]
                    ))

        # 2. Check Telemetry Discrepancies (e.g. PIP vs Intake Pressure)
        tel_items = [i for i in items if i.evidence_type == EvidenceType.TELEMETRY]
        pip_readings = [i for i in tel_items if "intake_pressure" in i.source_id or "pip" in i.source_id]
        if len(pip_readings) >= 2:
            val1, val2 = float(pip_readings[0].value or 0), float(pip_readings[1].value or 0)
            if abs(val1 - val2) > 50.0:  # >50 psi discrepancy
                conflicts.append(EvidenceConflict(
                    conflict_id=f"CONF-TEL-{uuid.uuid4().hex[:6]}",
                    evidence_refs=[pip_readings[0].evidence_id, pip_readings[1].evidence_id],
                    conflict_type="TELEMETRY_DISCREPANCY",
                    values={pip_readings[0].source_id: val1, pip_readings[1].source_id: val2},
                    authority_comparison="Sensor tag telemetry comparison",
                    impact="MEDIUM",
                    resolution_status="SURFACED",
                    resolution_method="Flag sensor variance exceeding 50 psi threshold.",
                    next_verification=["1. Verify transmitter calibration.", "2. Check telemetry wiring."]
                ))

        return conflicts
