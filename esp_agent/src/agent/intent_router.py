"""
3-Path Intent Router for ESP Agentic Platform
Grounded in PHASE_4_Objective_Layer_Implementation_Plan_ESP_APM.docx §26

Routing Paths:
1. Path A (Deterministic): Keyword / exact phrase matching against objective intent_classes
2. Path B (Semantic): Concept & similarity matching against objective descriptions and intents
3. Path C (Event): Direct mapping from events via ObjectiveRegistry (Single Authority)
4. Path LLM (Fallback): LLM classifier when keyword+semantic both below confidence threshold
"""

import logging
import re
from typing import NamedTuple, Optional, Dict, Any, List

from src.agent.objective_registry import ObjectiveRegistry

logger = logging.getLogger(__name__)

# ── B2: Threshold below which we mark ambiguous and may ask a question ────────
_AMBIGUITY_CONFIDENCE_THRESHOLD = 0.65
# ── B4: Threshold below which we try the LLM fallback before giving up ───────
_LLM_FALLBACK_THRESHOLD = 0.60


class RouteResult(NamedTuple):
    """
    Result of IntentRouter.route().
    Backward-compatible: callers that unpack (obj_id, conf, path) still work
    because NamedTuple supports positional unpacking of the first 3 fields.
    Use is_ambiguous for B3 clarification gating.
    """
    objective_id: str
    confidence: float
    path: str
    is_ambiguous: bool = False


class IntentRouter:
    """
    3-Path Intent Router that classifies queries or events into Level-2 Objective IDs.
    Delegates Path C (Event) routing directly to ObjectiveRegistry.
    Returns RouteResult (objective_id, confidence, path, is_ambiguous).
    """

    # ── B4.T2: Generalised greeting bucket ───────────────────────────────────
    # _GREETING_EXACT: full-message social openers only.
    # _GREETING_PREFIX: patterns that are ALWAYS social openers regardless of suffix.
    # Deliberately excludes "morning,", "afternoon,", "evening," — time-of-day words
    # followed by a request ("morning, can you check...") are operational, not small-talk.
    _GREETING_EXACT = {
        "hi", "hello", "hey", "who are you", "what can you do",
        "help", "role", "identity", "good morning", "good afternoon",
        "good evening", "morning", "afternoon", "evening"
    }
    _GREETING_PREFIX = ("hi ", "hello ", "hey ")

    def __init__(self, registry: Optional[ObjectiveRegistry] = None):
        self.registry = registry or ObjectiveRegistry()
        self._llm_gateway = None   # lazy-init to avoid circular import at startup

    def _get_llm_gateway(self):
        if self._llm_gateway is None:
            try:
                from src.llm.gateway import LLMGateway
                self._llm_gateway = LLMGateway()
            except Exception as ex:
                logger.warning("IntentRouter: LLM gateway unavailable for fallback (%s)", ex)
        return self._llm_gateway

    def _llm_classify(self, user_query: str) -> Optional[RouteResult]:
        """
        B4.T1 — Lightweight LLM classifier fallback.
        Asks the office-server LLM to map free-form language → exactly one objective_id.
        Only called when keyword+semantic both < _LLM_FALLBACK_THRESHOLD.
        Returns RouteResult or None if the LLM call fails.
        """
        gw = self._get_llm_gateway()
        if gw is None:
            return None

        objectives = self.registry.list_all()
        obj_list = "\n".join(
            f"- {o.objective_id}: {o.title}"
            for o in objectives
            if o.objective_id not in ("OP00_OPERATIONAL_CONTROL", "OBJ_OPERATIONAL_CONTROL")
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an ESP pump monitoring assistant.\n"
                    "Classify the operator query into exactly ONE of the objective IDs below.\n"
                    "If the query asks to check status, inspect health, or diagnose a problem on a well, choose OP01_CURRENT_STATUS or OP03_FAULT_DIAGNOSIS.\n"
                    "If the query is casual slang, greeting, general banter, or non-technical conversation, choose OP07_GENERAL_INQUIRY.\n"
                    "Reply with only the objective_id, nothing else.\n\n"
                    f"Objectives:\n{obj_list}"
                ),
            },
            {"role": "user", "content": user_query},
        ]

        try:
            resp = gw.chat(messages=messages, max_tokens=20, temperature=0.0)
            raw = (resp.content or "").strip().upper()
            # Validate the returned id exists in registry
            for obj in objectives:
                if obj.objective_id in raw:
                    logger.info(
                        "IntentRouter Path LLM: '%s' → %s", user_query[:40], obj.objective_id
                    )
                    return RouteResult(obj.objective_id, 0.75, "Path_LLM_Fallback", False)

            # Option A: If the LLM replied conversationally without emitting an exact objective ID,
            # treat it as general inquiry / conversational small talk rather than failing silently.
            if raw:
                logger.info(
                    "IntentRouter Path LLM: Conversational response ('%s') on '%s' → defaulting to OP07_GENERAL_INQUIRY",
                    raw[:40], user_query[:40]
                )
                return RouteResult("OP07_GENERAL_INQUIRY", 0.75, "Path_LLM_Fallback", False)
        except Exception as ex:
            logger.warning("IntentRouter: LLM fallback call failed (%s)", ex)
        return None

    def route(
        self,
        user_query: str,
        event_code: Optional[str] = None,
        conversation_context: Optional[Dict[str, Any]] = None,
    ) -> RouteResult:
        """
        Classify intent using 3-Path strategy + optional LLM fallback.
        Returns RouteResult(objective_id, confidence, path, is_ambiguous).

        Backward-compatible: callers that unpack (obj_id, conf, path) = route(...) still work.

        Args:
            user_query:           The raw operator query string.
            event_code:           Optional SCADA/MQTT event code (Path C).
            conversation_context: Optional dict with keys:
                                    last_well      – most recent well_id in session
                                    last_objective – objective_id from the prior turn
                                    recent_turns   – list of recent turn dicts
                                  When None, behaviour is identical to pre-A2 (A2.T3).
        """
        # ── A2.T2 / B2: Follow-up resolution ─────────────────────────────────
        _FOLLOWUP_TOKENS = {
            "why", "is that bad", "what about it", "explain", "elaborate",
            "tell me more", "and?", "so?", "what does that mean", "how bad",
            "what now", "what next", "what should i do", "ok and",
        }
        if conversation_context:
            last_obj = conversation_context.get("last_objective")
            q_stripped = user_query.lower().strip().rstrip("?.,!")
            if last_obj and q_stripped in _FOLLOWUP_TOKENS:
                logger.info(
                    "IntentRouter Path A (Follow-up): '%s' → carry forward %s",
                    user_query[:40], last_obj,
                )
                return RouteResult(last_obj, 0.90, "Path_A_FollowUp", False)

        # Path C: Direct Event Mapping via ObjectiveRegistry (Single Authority)
        if event_code:
            target_id = self.registry.resolve_event_mapping(event_code)
            if target_id:
                logger.info("IntentRouter Path C (Event): Mapped event '%s' -> %s", event_code, target_id)
                return RouteResult(target_id, 1.0, "Path_C_Event", False)

        q_lower = user_query.lower().strip()

        # ── B4.T2: Generalised greeting / small-talk bucket (Option C) ───────────
        # Elongated casual variants ("hiiiii", "heyyy", "heeeello", "hiiiii!") collapse
        # repeated letters and strip trailing punctuation before matching, so they land in OP07
        # instead of falling through to the ambiguous/clarification path.
        q_clean = q_lower.rstrip("!?. ,")
        q_collapsed = re.sub(r"([a-z])\1{2,}", r"\1", q_clean)
        if (
            q_clean in self._GREETING_EXACT
            or q_collapsed in self._GREETING_EXACT
            or any(q_clean.startswith(p) for p in self._GREETING_PREFIX)
            or any(q_collapsed.startswith(p) for p in self._GREETING_PREFIX)
        ):
            logger.info("IntentRouter Path A (Greeting): Small talk / greeting detected.")
            return RouteResult("OP07_GENERAL_INQUIRY", 0.98, "Path_A_Greeting", False)

        objectives = self.registry.list_all()

        # Detect fleet / multi-asset intent signals early
        is_fleet_query = any(w in q_lower for w in [
            "fleet", "all wells", "all assets", "which wells", "rank",
            "across the field", "entire field", "total field", "between fs-", "compare the installed"
        ])
        has_specific_asset = bool(re.search(r"\b(fs-\d+|fsws-\d+|well-\w+)\b", q_lower))

        # Path A: Specificity-First Deterministic & Variant Keyword Matching
        rules: List = []
        for obj in objectives:
            is_safety = obj.objective_id in ("OP00_OPERATIONAL_CONTROL", "OBJ_OPERATIONAL_CONTROL")
            is_fleet_obj = (obj.scope == "fleet" or
                            any(obj.objective_id.startswith(p) for p in ("OP08","OP09","OP10","OP11","OP12","OP13")))
            base_prio = (100 if is_safety else
                         (20 if (is_fleet_query and is_fleet_obj) else
                          (15 if (not is_fleet_query and not is_fleet_obj) else 1)))

            for kw in obj.intent_classes:
                rules.append((kw, obj.objective_id, 0.95, "Path_A_Deterministic", base_prio))
            for var in obj.workflow_variants:
                for kw in var.intent_classes:
                    rules.append((kw, obj.objective_id, 0.96, f"Path_A_Variant_{var.variant_id}", base_prio + 2))

        rules.sort(key=lambda r: (r[4], len(r[0].split()), len(r[0])), reverse=True)

        for kw, obj_id, conf, path_lbl, _ in rules:
            kw_lower = kw.lower()
            pattern = r"\b" + re.escape(kw_lower) + r"\b"
            if re.search(pattern, q_lower):
                logger.info("IntentRouter %s: Keyword '%s' -> %s", path_lbl, kw, obj_id)
                return RouteResult(obj_id, conf, path_lbl, False)

        # Path B: Semantic Heuristic / Keyword Overlap Fallback
        HARD_REFUSAL_IDS = {"OP00_OPERATIONAL_CONTROL", "OBJ_OPERATIONAL_CONTROL"}
        is_fleet_query = any(w in q_lower for w in [
            "fleet", "all wells", "all assets", "which wells", "rank", "across the field"
        ])
        has_specific_asset = bool(re.search(r"\b(fs-\d+|fsws-\d+|well-\w+)\b", q_lower))

        # Conversational / generic stop words to avoid false positive substring/token matching
        STOP_WORDS = {
            "the", "and", "why", "how", "for", "are", "can", "you", "give", "get",
            "got", "all", "any", "not", "but", "who", "his", "her", "its", "our",
            "out", "now", "see", "too", "use", "way", "yet", "low", "down", "bug",
            "this", "that", "there", "then", "with", "from", "have", "been", "was",
            "were", "what", "when", "where", "which", "will", "would", "could",
            "should", "about", "into", "over", "some", "take", "look", "things",
            "morning", "afternoon", "evening", "please", "check", "tell", "show",
            "well", "wells", "asset", "assets", "pump", "pumps", "okay", "good",
            "fsws", "well"
        }
        query_tokens = set(re.findall(r"\b[a-z]{3,}\b", q_lower)) - STOP_WORDS

        best_score = 0.0
        best_obj_id = "OP03_FAULT_DIAGNOSIS"

        for obj in objectives:
            if obj.objective_id in HARD_REFUSAL_IDS or obj.objective_id == "OP07_GENERAL_INQUIRY":
                continue

            title_tokens = set(re.findall(r"\b[a-z]{3,}\b", obj.title.lower()))
            desc_tokens = set(re.findall(r"\b[a-z]{3,}\b", obj.description.lower()))

            kw_matches = query_tokens & title_tokens
            desc_matches = query_tokens & desc_tokens

            keyword_score = len(kw_matches) * 0.2 + len(desc_matches) * 0.1
            score = keyword_score

            # Only apply scope / asset tie-breaker if there is some keyword affinity
            if keyword_score > 0:
                if is_fleet_query and obj.scope == "fleet":
                    score += 0.35
                elif has_specific_asset and obj.scope == "single":
                    score += 0.25

            if score > best_score:
                best_score = score
                best_obj_id = obj.objective_id

        semantic_confidence = min(0.85, 0.5 + best_score)

        # ── B2.T1/T2: Ambiguity signal — compute before LLM hop ──────────────
        # Mark ambiguous when confidence is below threshold AND no known well
        # (either from session memory or named explicitly in query) anchors the query.
        has_known_well = bool(
            (conversation_context and conversation_context.get("last_well"))
            or has_specific_asset
        )
        is_ambiguous = (semantic_confidence < _AMBIGUITY_CONFIDENCE_THRESHOLD and not has_known_well)

        # ── B4.T3: Short-circuit — only call LLM fallback when semantic is weak ──
        if semantic_confidence < _LLM_FALLBACK_THRESHOLD:
            llm_result = self._llm_classify(user_query)
            if llm_result is not None:
                # LLM resolved intent but asset ambiguity is independent: if the
                # query had no well context and low semantic confidence, the operator
                # still hasn't told us WHICH asset — so preserve is_ambiguous.
                return RouteResult(llm_result.objective_id, llm_result.confidence,
                                   llm_result.path, is_ambiguous)

        logger.info(
            "IntentRouter Path B (Semantic): Query '%s...' -> %s (conf=%.2f, ambiguous=%s)",
            user_query[:30], best_obj_id, semantic_confidence, is_ambiguous,
        )
        return RouteResult(best_obj_id, semantic_confidence, "Path_B_Semantic", is_ambiguous)
