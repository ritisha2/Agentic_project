"""
Layered Prompt Architecture — Phase 10: LLM Layer Architecture
Grounded in ESP APM LLM Architecture Design §3

Avoids monolithic prompts. Composes layered prompts dynamically:
  SYSTEM_PROMPT (Role, safety, evidence requirements, no fabrication)
        +
  ESP_DOMAIN_RULES (Physical hydraulic boundaries, pump curves, gas slugging)
        +
  OBJECTIVE_PROMPTS (Task-specific goal: RCA, fault diagnosis, RUL, maintenance)
        +
  COMPACT_CONTEXT (JSON context block built by CompactContextBuilder)
        +
  OUTPUT_SCHEMA_INSTRUCTIONS (Pydantic JSON format rules)
"""

import json
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# 1. System Prompt Layer
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are Agent Jane, an expert AI Industrial Equipment Supervisor specializing in Electrical Submersible Pump (ESP) Artificial Lift systems.

CORE DIRECTIVES:
1. Ground every claim strictly in provided telemetry, engineering calculations, and evidence IDs.
2. NEVER fabricate telemetry values, sensor readings, or physics equations.
3. If data is missing or uncertain, state the uncertainty explicitly in the 'uncertainties' list.
4. All recommendations are ADVISORY-ONLY. You do not possess direct actuation authority over SCADA equipment.
5. Provide actionable, evidence-backed findings that can be verified by a field operator.
6. Your response MUST be a single, valid JSON object conforming strictly to the required schema.
"""


# ---------------------------------------------------------------------------
# 2. ESP Domain Rules Layer
# ---------------------------------------------------------------------------
ESP_DOMAIN_RULES = """ESP DOMAIN DIAGNOSTIC RULES:
- Intake Gas Interference: Cyclical PIP acoustic spikes, motor amp dips, GOR > 500 scf/bbl, pump operating left of BEP.
- Mechanical Pump Wear: Linear head decline (-15%+), stable motor current, non-recovering TDH reduction.
- Electrical Motor Overheating: Motor temperature > 130°C, winding insulation breakdown risk, drive current spiking.
- Scale / Plugging: Discharge pressure drop, rising motor load, differential pressure reduction across pump stages.
- Dry-Well Pump-off: PIP drops below minimum submergence limit (< 200 psi), flow rate drops sharply to 0 BPD.
"""


# ---------------------------------------------------------------------------
# 3. Objective Prompts Layer
# ---------------------------------------------------------------------------
OBJECTIVE_PROMPTS: Dict[str, str] = {
    "OP01_PRODUCTION_DECLINE": """OBJECTIVE: Root Cause Analysis for ESP Production Decline.
Task Requirements:
1. Analyze liquid flow rate decline against baseline TDH and BEP curves.
2. Differentiate between Intake Gas Interference (slugging) vs Mechanical Pump Wear.
3. Reference specific frozen evidence IDs (e.g. EV-001, EV-007) in hypotheses.
4. Recommend actionable operator verification checklist.
""",
    "OP02_MOTOR_FAULT": """OBJECTIVE: ESP Electrical Motor Thermal & Insulation Risk Assessment.
Task Requirements:
1. Evaluate motor winding temperature trends and current stability.
2. Assess 24h thermal overload risk and remaining useful life (RUL).
3. Identify immediate cooling, frequency reduction, or trip mitigation.
""",
    "OP03_FAULT_DIAGNOSIS": """OBJECTIVE: Comprehensive Multi-Hypothesis ESP Fault Classification.
Task Requirements:
1. Compare physics-based model outputs against ML classifier scores.
2. Resolve potential conflicts between telemetry trends and ML predictions.
3. Assign confidence scores (0.0 to 1.0) to top 2 failure mode hypotheses.
""",
    "OP04_MAINTENANCE_PREDICTION": """OBJECTIVE: Predictive Maintenance & RUL Optimization.
Task Requirements:
1. Estimate remaining useful life and failure mode progression.
2. Recommend preventive workover window or VSD speed adjustment.
""",
}

DEFAULT_OBJECTIVE_PROMPT = """OBJECTIVE: ESP Operational Performance Diagnostic.
Task Requirements:
1. Evaluate available telemetry and engineering metrics.
2. Formulate evidence-grounded hypotheses for any operational anomalies.
3. Recommend safe operator verification steps under Advisory-Only lock.
"""


# ---------------------------------------------------------------------------
# 4. Output Schema Prompt Layer
# ---------------------------------------------------------------------------
OUTPUT_SCHEMA_INSTRUCTION = """OUTPUT REQUIREMENT:
You MUST respond with a single, strictly formatted JSON object matching this schema:
{
  "assessment": "<executive summary sentence>",
  "hypotheses": [
    {
      "cause": "<primary hypothesis cause name>",
      "confidence": <float between 0.0 and 1.0>,
      "supporting_evidence": ["<EV-ID1>", "<EV-ID2>"],
      "contradicting_evidence": []
    }
  ],
  "uncertainties": ["<any missing data or unverified assumptions>"],
  "recommendation": "<actionable recommendation>",
  "verification": "<operator verification checklist>"
}

Do NOT wrap the response in markdown blocks if raw JSON is requested. Do NOT include conversational prose before or after the JSON.
"""


# ---------------------------------------------------------------------------
# Prompt Composer
# ---------------------------------------------------------------------------
class LayeredPromptBuilder:
    """
    Composes system prompt, domain rules, objective prompts, and compact context
    into a structured message list ready for the LLM Gateway.
    """

    @staticmethod
    def build_chat_messages(
        compact_context: Dict[str, Any],
        user_query: Optional[str] = None,
        custom_system_prompt: Optional[str] = None,
    ) -> list[Dict[str, str]]:
        """
        Build Open-AI style message array:
        [
          {"role": "system", "content": SYSTEM_PROMPT + DOMAIN_RULES},
          {"role": "user", "content": OBJECTIVE_PROMPT + COMPACT_CONTEXT + USER_QUERY + SCHEMA_INSTRUCTION}
        ]
        """
        # System prompt layer
        system_content = (custom_system_prompt or SYSTEM_PROMPT) + "\n\n" + ESP_DOMAIN_RULES

        # Objective layer
        obj_id = compact_context.get("objective", "")
        obj_prompt = OBJECTIVE_PROMPTS.get(obj_id, DEFAULT_OBJECTIVE_PROMPT)

        # Context layer (compact JSON string)
        context_json = json.dumps(compact_context, indent=2)

        # User payload layer
        user_parts = [
            obj_prompt,
            "--- COMPACT OPERATIONAL CONTEXT ---",
            context_json,
            "----------------------------------",
        ]

        if user_query:
            user_parts.append(f"OPERATOR QUERY: {user_query}")

        user_parts.append("\n" + OUTPUT_SCHEMA_INSTRUCTION)
        user_content = "\n\n".join(user_parts)

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]
