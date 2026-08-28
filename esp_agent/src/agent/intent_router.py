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

        # Path A: Deterministic Keyword Matching
        # Word-boundary matching to avoid false positives from short keywords appearing
        # as substrings inside unrelated words (e.g. "hi" inside "this"/"which").
        objectives = self.registry.list_all()
        for obj in objectives:
            for kw in obj.intent_classes:
                kw_lower = kw.lower()
                pattern = r"\b" + re.escape(kw_lower) + r"\b"
                if re.search(pattern, q_lower):
                    logger.info(f"IntentRouter Path A (Deterministic): Keyword '{kw}' -> {obj.objective_id}")
                    return obj.objective_id, 0.95, "Path_A_Deterministic"

        # Path B: Semantic Heuristic / Keyword Overlap Fallback
        best_score = 0.0
        best_obj_id = "OP03_FAULT_DIAGNOSIS"  # Default objective

        for obj in objectives:
            score = 0.0
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
