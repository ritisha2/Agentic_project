"""
3-Path Intent Router for ESP Agentic Platform
Grounded in PHASE_4_Objective_Layer_Implementation_Plan_ESP_APM.docx §26

Routing Paths:
1. Path A (Deterministic): Keyword / exact phrase matching against objective intent_classes
2. Path B (Semantic): Concept & similarity matching against objective descriptions and intents
3. Path C (Event): Direct mapping from events via ObjectiveRegistry (Single Authority)
"""

import logging
import re
from typing import Tuple, Optional, Dict, Any

from src.agent.objective_registry import ObjectiveRegistry
from src.schemas.objective import ObjectiveDefinition

logger = logging.getLogger(__name__)


class IntentRouter:
    """
    3-Path Intent Router that classifies queries or events into Level-2 Objective IDs.
    Delegates Path C (Event) routing directly to ObjectiveRegistry.
    """

    def __init__(self, registry: Optional[ObjectiveRegistry] = None):
        self.registry = registry or ObjectiveRegistry()

    def route(
        self,
        user_query: str,
        event_code: Optional[str] = None
    ) -> Tuple[str, float, str]:
        """
        Classify intent using 3-Path strategy.
        Returns: (objective_id: str, confidence: float, path_used: str)
        """
        # Path C: Direct Event Mapping via ObjectiveRegistry (Single Authority)
        if event_code:
            target_id = self.registry.resolve_event_mapping(event_code)
            if target_id:
                logger.info(f"IntentRouter Path C (Event): Mapped event '{event_code}' -> {target_id}")
                return target_id, 1.0, "Path_C_Event"

        q_lower = user_query.lower().strip()

        # Conversational greeting & identity check
        if q_lower in ["hi", "hello", "hey", "who are you", "what can you do", "help", "role", "identity"] or any(q_lower.startswith(g) for g in ["hi ", "hello ", "hey "]):
            logger.info("IntentRouter Path A (Greeting): Small talk / greeting detected.")
            return "OP07_GENERAL_INQUIRY", 0.98, "Path_A_Greeting"

        objectives = self.registry.list_all()

        # Detect fleet / multi-asset intent signals early
        is_fleet_query = any(w in q_lower for w in ["fleet", "all wells", "all assets", "which wells", "rank", "across the field", "entire field", "total field", "between fs-", "compare the installed"])
        has_specific_asset = bool(re.search(r"\b(fs-\d+|fsws-\d+|well-\w+)\b", q_lower))

        # Path A: Specificity-First Deterministic & Variant Keyword Matching
        rules = []
        for obj in objectives:
            is_safety = obj.objective_id in ("OP00_OPERATIONAL_CONTROL", "OBJ_OPERATIONAL_CONTROL")
            is_fleet_obj = obj.scope == "fleet" or obj.objective_id.startswith("OP08") or obj.objective_id.startswith("OP09") or obj.objective_id.startswith("OP10") or obj.objective_id.startswith("OP11") or obj.objective_id.startswith("OP12") or obj.objective_id.startswith("OP13")

            base_prio = 100 if is_safety else (20 if (is_fleet_query and is_fleet_obj) else (15 if (not is_fleet_query and not is_fleet_obj) else 1))

            for kw in obj.intent_classes:
                rules.append((kw, obj.objective_id, 0.95, "Path_A_Deterministic", base_prio))

            for var in obj.workflow_variants:
                for kw in var.intent_classes:
                    rules.append((kw, obj.objective_id, 0.96, f"Path_A_Variant_{var.variant_id}", base_prio + 2))

        # Sort globally by: priority (descending), word count (descending), character length (descending)
        rules.sort(key=lambda r: (r[4], len(r[0].split()), len(r[0])), reverse=True)

        for kw, obj_id, conf, path_lbl, _ in rules:
            kw_lower = kw.lower()
            pattern = r"\b" + re.escape(kw_lower) + r"\b"
            if re.search(pattern, q_lower):
                logger.info(f"IntentRouter {path_lbl}: Keyword '{kw}' -> {obj_id}")
                return obj_id, conf, path_lbl

        # Path B: Semantic Heuristic / Keyword Overlap Fallback with Scope Tie-Breaking
        HARD_REFUSAL_OBJECTIVE_IDS = {"OP00_OPERATIONAL_CONTROL", "OBJ_OPERATIONAL_CONTROL"}
        is_fleet_query = any(w in q_lower for w in ["fleet", "all wells", "all assets", "which wells", "rank", "across the field"])
        has_specific_asset = bool(re.search(r"\b(fs-\d+|fsws-\d+|well-\w+)\b", q_lower))

        best_score = 0.0
        best_obj_id = "OP03_FAULT_DIAGNOSIS"  # Default objective

        for obj in objectives:
            if obj.objective_id in HARD_REFUSAL_OBJECTIVE_IDS:
                continue
            score = 0.0

            # Scope bonus/penalty to prevent single vs fleet collisions
            if is_fleet_query and obj.scope == "fleet":
                score += 0.35
            elif has_specific_asset and obj.scope == "single":
                score += 0.25

            # Check overlap with title & description
            words = q_lower.split()
            for w in words:
                if len(w) > 3:
                    if w in obj.title.lower():
                        score += 0.2
                    if w in obj.description.lower():
                        score += 0.1
            
            if score > best_score:
                best_score = score
                best_obj_id = obj.objective_id

        confidence = min(0.85, 0.5 + best_score)
        logger.info(f"IntentRouter Path B (Semantic): Query '{user_query[:30]}...' -> {best_obj_id} (conf={confidence:.2f})")
        return best_obj_id, confidence, "Path_B_Semantic"
