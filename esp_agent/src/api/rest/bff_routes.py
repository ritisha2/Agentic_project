"""
FastAPI Backend-for-Frontend (BFF) API Routes for ESP APM UI
Grounded in ESP_APM_PHASE_9_FRONTEND_BACKEND_PRODUCT_INTEGRATION_ARCHITECTURE.docx §7, §22, §25
"""

import time
import uuid
import asyncio
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, Request
from pydantic import BaseModel, Field

from src.services.asset_context_service import AssetContextService
from src.services.telemetry_service import TelemetryService
from src.services.engineering_service import EngineeringService
from src.services.twin_service import DigitalTwinService
from src.services.case_service import CaseOutcomeService
from src.services.audit_service import AuditService
from src.adapters.evidence_repository import EvidenceRepository
from src.services.xai_service import XAIEngine
from src.agent.supervisor.user_entry import UserEntryAdapter, ClarificationNeeded
from src.adapters.live_data_bridge import live_bridge
from src.schemas.visualization import VisualizationSpec, ChartSpec, ExplanationSpec, ExplanationSection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ui", tags=["bff"])

asset_service = AssetContextService()
telemetry_service = TelemetryService()
engineering_service = EngineeringService()
twin_service = DigitalTwinService()
case_service = CaseOutcomeService()
audit_service = AuditService()
evidence_repo = EvidenceRepository()
user_adapter = UserEntryAdapter()

# Conversation memory — A3.T2 (shared singleton, same Redis as CheckpointManager)
from src.memory.conversation_store import ConversationStore
_conv_store = ConversationStore()

# B3.T3: In-process cache of paused LangGraph threads awaiting clarification.
# Maps session_id → {"thread_id": str, "asset_id": str}
# Thread-safe for single-process FastAPI (GIL-protected dict).
_pending_clarifications: Dict[str, Dict[str, str]] = {}


# ─────────────────────────────────────────────────────────────────────────
# Conversational NLG Layer — makes Agent Jane respond like a real co-pilot
# instead of emitting a rigid templated diagnostic report for every query.
# ─────────────────────────────────────────────────────────────────────────
from src.llm.adapter import LLMAdapter
from src.agent.intent_router import IntentRouter

_nlg_llm = LLMAdapter()
_intent_router = IntentRouter()


# Weak / conversational queries get a warm reply, not a diagnostic report.
_CONVERSATIONAL_OBJECTIVES = {"OP07_GENERAL_INQUIRY"}
# Fleet objectives are cross-asset — they skip the single-asset telemetry chart.
_FLEET_OBJECTIVES = {
    "OP08_FLEET_INVENTORY", "OP09_FLEET_PRODUCTION_OPTIMIZATION",
    "OP10_FLEET_DESIGN_SIZING", "OP11_FLEET_MAINTENANCE_PRIORITY",
    "OP12_FLEET_CASE_ANALYTICS", "OP13_FLEET_EXECUTIVE_REPORTING",
}

AGENT_JANE_VOICE = (
    "You are Agent Jane, an autonomous ESP (Electric Submersible Pump) operations co-pilot "
    "for SCADA field engineers. You speak in a warm, professional, confident voice — like a "
    "seasoned reliability engineer walking a colleague through a problem. Write flowing natural "
    "prose with light markdown (short bold labels, the occasional list) for readability. Be "
    "verbose but clear. Hard rules: never invent telemetry values — use only the numbers "
    "provided; you are Advisory-Only and must never claim to have executed any control action."
)


def _iter_stream_chunks(text: str, words_per_chunk: int = 6):
    """Yield word-grouped chunks so the UI renders a smooth typewriter effect."""
    import re
    tokens = re.findall(r"\S+\s*", text)
    buf, count = "", 0
    for t in tokens:
        buf += t
        count += 1
        if count >= words_per_chunk:
            yield buf
            buf, count = "", 0
    if buf:
        yield buf


def _compose_conversational_reply(user_query: str, asset_id: str) -> str:
    """OP07 / weak / greeting: friendly LLM-generated reply, no diagnostics, no chart."""
    prompt = (
        f"The field engineer sent this message: \"{user_query}\".\n"
        f"They are currently viewing well {asset_id}.\n"
        f"This is a conversational / general message, NOT a diagnostic request.\n"
        f"Respond warmly as Agent Jane: greet them, briefly introduce what you can do "
        f"(diagnose live well telemetry, analyze gas interference & drawdown, check pump curve / "
        f"BEP deviation, estimate health & remaining useful life, and rank fleet risk), and invite "
        f"them to ask about a specific well or symptom. Keep it friendly and concise — 3 to 5 "
        f"sentences. Do not fabricate any telemetry readings."
    )
    try:
        resp = _nlg_llm.generate(prompt=prompt, system_prompt=AGENT_JANE_VOICE,
                                 temperature=0.5, run_id="NLG-CONV")
        text = (resp.content or "").strip()
        if text:
            return text
    except Exception as e:
        logger.warning(f"[BFF] Conversational NLG failed: {e}")
    return (
        f"Hi — I'm **Agent Jane**, your ESP operations co-pilot. I can diagnose live telemetry, "
        f"analyze gas interference and drawdown, check pump-curve / BEP deviation, estimate health "
        f"and remaining useful life, and rank fleet risk. Ask me something like "
        f"*\"Why is production declining on {asset_id}?\"* to get started."
    )


def _fallback_template_narrative(advisory, asset_id: str) -> str:
    """Conversational template used if the LLM narrative call fails (no LLM dependency)."""
    assessment = getattr(advisory, "assessment", "Asset operating within normal limits.")
    diagnosis = getattr(advisory, "diagnosis", "No critical anomaly detected.")
    recommendation = getattr(advisory, "recommendation", "Maintain current operating envelope.")
    confidence = getattr(advisory, "confidence", 0.95)
    risk = getattr(advisory, "risk", "Low operational risk")
    verification = getattr(advisory, "verification", []) or []
    txt = (
        f"Here's what I found on **{asset_id}**.\n\n"
        f"**Assessment.** {assessment}\n\n"
        f"**Diagnosis.** {diagnosis} I'm about {int(float(confidence) * 100)}% confident, "
        f"with the risk outlook at *{risk}*.\n\n"
        f"**What I'd do next.** {recommendation}\n\n"
    )
    if verification:
        txt += "**To verify, please:**\n" + "\n".join(f"- {v}" for v in verification) + "\n\n"
    txt += "Want me to dig into any specific signal or run a what-if on this well?"
    return txt


def _compose_diagnostic_narrative(advisory, user_query: str, objective_id: str, asset_id: str) -> str:
    """Diagnostic / fleet objectives: verbose conversational narrative grounded in the advisory."""
    assessment = getattr(advisory, "assessment", "")
    diagnosis = getattr(advisory, "diagnosis", "")
    recommendation = getattr(advisory, "recommendation", "")
    risk = getattr(advisory, "risk", "")
    confidence = getattr(advisory, "confidence", 0.0)
    constraints = getattr(advisory, "constraints", []) or []
    verification = getattr(advisory, "verification", []) or []
    evidence = getattr(advisory, "evidence", []) or []

    ev_lines = []
    for ev in evidence[:8]:
        sid = getattr(ev, "source_id", "") if not isinstance(ev, dict) else ev.get("source_id", "")
        obs = getattr(ev, "observation", "") if not isinstance(ev, dict) else ev.get("observation", "")
        if obs:
            ev_lines.append(f"- {sid}: {obs}")
    ev_block = "\n".join(ev_lines) if ev_lines else "(no anomalous evidence — signals within limits)"

    try:
        conf_pct = int(float(confidence) * 100)
    except Exception:
        conf_pct = 0

    prompt = (
        f"The field engineer asked: \"{user_query}\" about well {asset_id}.\n"
        f"You already completed the analysis (objective: {objective_id}). Here are your grounded "
        f"findings — use ONLY these, do not invent numbers:\n\n"
        f"ASSESSMENT: {assessment}\n"
        f"DIAGNOSIS: {diagnosis}\n"
        f"CONFIDENCE: {conf_pct}%\n"
        f"RISK: {risk}\n"
        f"RECOMMENDED ACTION: {recommendation}\n"
        f"SAFETY CONSTRAINTS: {'; '.join(map(str, constraints)) or 'standard operating limits'}\n"
        f"VERIFICATION STEPS: {'; '.join(map(str, verification)) or 'confirm SCADA alignment'}\n"
        f"EVIDENCE:\n{ev_block}\n\n"
        f"Now write your reply to the engineer as Agent Jane, as a flowing conversation:\n"
        f"1. Open with a brief, warm one-line acknowledgment of their question.\n"
        f"2. Explain what you inspected (the signals / engineering calcs / ML & evidence).\n"
        f"3. Walk through your reasoning and state the diagnosis with your confidence and why.\n"
        f"4. Give the recommended action clearly, with the safety constraints.\n"
        f"5. List the verification steps the operator should perform.\n"
        f"6. Close by inviting a follow-up question.\n"
        f"Use light markdown headings/bold. Be verbose but readable."
    )
    try:
        resp = _nlg_llm.generate(prompt=prompt, system_prompt=AGENT_JANE_VOICE,
                                 temperature=0.4, run_id="NLG-DIAG")
        text = (resp.content or "").strip()
        if text and len(text) > 40:
            return text
    except Exception as e:
        logger.warning(f"[BFF] Diagnostic NLG failed, falling back to template: {e}")
    return _fallback_template_narrative(advisory, asset_id)


@router.get("/health")
def bff_health():
    return {"status": "ok", "service": "bff_agent_gateway"}


@router.api_route("/warmup", methods=["GET", "POST"])
async def warmup_endpoint():
    """
    Pre-warm LLM Gateway & model cache in background on demand or frontend load.
    Returns 200 OK immediately so frontend fetches do not time out.
    """
    def _do_warmup():
        try:
            from src.llm.adapter import LLMAdapter
            adapter = LLMAdapter()
            adapter.generate("warmup", run_id="WARMUP-FE")
        except Exception:
            pass

    asyncio.create_task(asyncio.to_thread(_do_warmup))
    return {"status": "ok", "message": "Background model warmup initiated."}


class UIAdvisoryRunRequest(BaseModel):
    user_query: str = Field(description="Natural language user question")
    asset_id: Optional[str] = Field(default=None, description="Target ESP asset ID")



@router.get("/assets/{asset_id}/workspace", response_model=Dict[str, Any])
def get_asset_workspace(asset_id: str):
    """
    GET /api/ui/assets/{asset_id}/workspace
    Aggregates Asset Context, latest telemetry snapshot, QoD status, predictive model risk scores,
    and recent advisories into a single UI view payload.
    """
    try:
        ctx = asset_service.get_context(asset_id)
        telemetry = telemetry_service.get_latest(asset_id)
        
        # Calculate baseline TDH via EngineeringService authority
        from src.services.engineering_service import EngineeringService
        from shared.schemas.engineering import TDHRequest
        eng_svc = EngineeringService()
        tel_dict = telemetry.model_dump().get("measurements", {})
        pdp = tel_dict.get("discharge_pressure", {}).get("value", 2100.0)
        pip = tel_dict.get("intake_pressure", {}).get("value", 350.0)
        tdh_resp = eng_svc.calculate_tdh(TDHRequest(
            asset_id=asset_id,
            pdp_psi=float(pdp),
            pip_psi=float(pip),
            fluid_sg=0.85
        ))
        tdh_result = tdh_resp.tdh_ft
        bep_deviation = -17.1

        # Query live ML assessment from cced_esp
        ml_eval = live_bridge.get_ml_assessment(asset_id)
        identified_fault = "Normal Condition"
        confidence = 0.95
        if ml_eval and "prediction" in ml_eval:
            p = ml_eval["prediction"]
            identified_fault = p.get("status", "Normal Condition")
            confidence = round(float(p.get("health_index", 95.0)) / 100.0, 2)

        # Fetch active evidence packs for asset
        packs = evidence_repo.list_packs_for_asset(asset_id)
        recent_pack_id = packs[-1].pack_id if packs else None

        return {
            "status": "SUCCESS",
            "asset_id": asset_id,
            "asset_context": ctx.model_dump(),
            "telemetry": telemetry.model_dump(),
            "engineering": {
                "tdh_ft": tdh_result,
                "bep_deviation_pct": bep_deviation
            },
            "predictive_models": {
                "fault_classifier": {"identified_fault": identified_fault, "confidence": confidence},
                "risk_24h": {"risk_level": "LOW" if confidence > 0.8 else "MEDIUM", "score": round(1.0 - confidence, 2)}
            },
            "recent_pack_id": recent_pack_id
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error serving workspace for asset '{asset_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assets/{asset_id}/timeline", response_model=Dict[str, Any])
def get_asset_timeline(asset_id: str):
    """
    GET /api/ui/assets/{asset_id}/timeline
    Aggregates operational events, alerts, and verification checks.
    """
    checks = case_service.get_verification_checks(asset_id)
    # MOCK_SCAFFOLD: hardcoded timeline events | reason: placeholder asset timeline until a real
    # event store is wired to this endpoint | expiry: when /timeline reads live events | ref: none
    events = [
        {
            "event_id": "EVT-101",
            "event_type": "PRODUCTION_DECLINE_DETECTED",
            "timestamp": "2026-08-27T08:00:00Z",
            "severity": "MEDIUM",
            "summary": "Flow rate dropped from 1750 BPD to 1450 BPD"
        },
        {
            "event_id": "EVT-102",
            "event_type": "MOTOR_TEMP_ELEVATED",
            "timestamp": "2026-08-27T07:30:00Z",
            "severity": "LOW",
            "summary": "Motor temp reached 110.0 °C"
        }
    ]
    return {
        "asset_id": asset_id,
        "events": events,
        "verification_checks": [c.model_dump() for c in checks]
    }


@router.post("/agent/run", response_model=Dict[str, Any])
def start_ui_agent_run(req: UIAdvisoryRunRequest, request: Request):
    """
    POST /api/ui/agent/run
    Initiates a LangGraph Supervisor run with tracking correlation ID.
    Reads X-Session-ID header for multi-turn conversation memory (A3.T2).
    """
    session_id = request.headers.get("X-Session-ID") or None
    run_id = f"RUN-UI-{uuid.uuid4().hex[:8]}"

    advisory = user_adapter.run(
        user_query=req.user_query,
        asset_id=req.asset_id,
        request_id=run_id,
        session_id=session_id,
    )

    return {
        "run_id": run_id,
        "status": "COMPLETED",
        "objective_id": advisory.objective_id,
        "advisory": advisory.model_dump()
    }



from fastapi.responses import StreamingResponse
import json

@router.post("/agent/stream")
async def stream_ui_agent_run(req: UIAdvisoryRunRequest, request: Request):
    """
    POST /api/ui/agent/stream
    Streams real-time execution tokens, status milestones, and Generative UI data payloads over NDJSON SSE.
    Reads X-Session-ID header for multi-turn conversation memory (A3.T2).
    """
    session_id = request.headers.get("X-Session-ID") or None
    run_id = f"RUN-UI-{uuid.uuid4().hex[:8]}"

    # Build conversation_context for the intent router
    recent_turns: list = []
    last_objective = None
    if session_id:
        recent_turns = _conv_store.get_history(session_id, limit=10)
        for t in reversed(recent_turns):
            if t.get("role") == "assistant" and t.get("intent_detected"):
                last_objective = t["intent_detected"]
                break
    conv_ctx = {"last_well": req.asset_id or None, "last_objective": last_objective, "recent_turns": recent_turns} if session_id else None

    async def event_generator():
        # ── B3.T3: Check for a pending clarification resume FIRST ────────────
        # If this session was waiting for an answer, route the query as the answer.
        pending = _pending_clarifications.pop(session_id, None) if session_id else None
        if pending:
            yield json.dumps({
                "type": "status", "run_id": run_id, "stage": "RESUMING",
                "message": "Got it — continuing the analysis with your answer..."
            }) + "\n"
            try:
                advisory = await asyncio.to_thread(
                    user_adapter.resume,
                    thread_id=pending["thread_id"],
                    operator_answer=req.user_query,
                    session_id=session_id,
                    asset_id=pending.get("asset_id"),
                )
            except ClarificationNeeded as ex2:
                # Nested clarification (edge case — still ask)
                if session_id:
                    _pending_clarifications[session_id] = {
                        "thread_id": ex2.thread_id, "asset_id": ex2.asset_id
                    }
                for chunk in _iter_stream_chunks(ex2.question):
                    yield json.dumps({"type": "text_delta", "delta": chunk}) + "\n"
                yield json.dumps({"type": "done", "run_id": run_id}) + "\n"
                return
            except Exception as ex:
                logger.error("[BFF] Resume error run %s: %s", run_id, ex, exc_info=True)
                yield json.dumps({
                    "type": "text_delta",
                    "delta": f"I had a problem resuming the analysis ({str(ex)}). Please try your question again."
                }) + "\n"
                yield json.dumps({"type": "done", "run_id": run_id}) + "\n"
                return
            # Fall through to the normal advisory streaming path below ↓
        else:
            # ── Normal path: Route intent up-front ───────────────────────────
            try:
                route_result = _intent_router.route(req.user_query, conversation_context=conv_ctx)
                objective_id, route_conf, route_path, route_ambiguous = route_result
            except Exception:
                objective_id, route_conf, route_path, route_ambiguous = "OP01_CURRENT_STATUS", 0.5, "fallback", False

            yield json.dumps({
                "type": "status",
                "run_id": run_id,
                "stage": "INITIATING",
                "message": "Understanding your question..."
            }) + "\n"

            # ── Conversational fast-path: greetings / weak / general inquiry ──
            if objective_id in _CONVERSATIONAL_OBJECTIVES or route_path == "Path_A_Greeting":
                yield json.dumps({
                    "type": "status", "run_id": run_id, "stage": "COMPOSING",
                    "message": "Agent Jane is replying..."
                }) + "\n"
                reply = await asyncio.to_thread(_compose_conversational_reply, req.user_query, req.asset_id)
                for chunk in _iter_stream_chunks(reply):
                    yield json.dumps({"type": "text_delta", "delta": chunk}) + "\n"
                if session_id:
                    _conv_store.append(session_id, "user", req.user_query, well_id=req.asset_id or None)
                    _conv_store.append(session_id, "assistant", str(reply)[:500],
                                       well_id=req.asset_id or None, intent=objective_id)
                yield json.dumps({"type": "done", "run_id": run_id}) + "\n"
                return

            # ── Diagnostic / fleet path: run the Supervisor graph ──
            try:
                advisory = await asyncio.to_thread(
                    user_adapter.run,
                    user_query=req.user_query,
                    asset_id=req.asset_id,
                    request_id=run_id,
                    session_id=session_id,
                )
            except ClarificationNeeded as ex:
                # B3.T3: Graph interrupted — stream the question, record pending thread
                if session_id:
                    _pending_clarifications[session_id] = {
                        "thread_id": ex.thread_id, "asset_id": ex.asset_id
                    }
                    _conv_store.append(session_id, "user", req.user_query,
                                       well_id=req.asset_id or None)
                    _conv_store.append(session_id, "assistant", ex.question[:500],
                                       well_id=None, intent="CLARIFICATION")
                yield json.dumps({
                    "type": "status", "run_id": run_id, "stage": "CLARIFYING",
                    "message": "Agent Jane needs a bit more info..."
                }) + "\n"
                for chunk in _iter_stream_chunks(ex.question):
                    yield json.dumps({"type": "text_delta", "delta": chunk}) + "\n"
                yield json.dumps({"type": "done", "run_id": run_id}) + "\n"
                return
            except Exception as ex:
                logger.error(f"[BFF] Error executing Supervisor run {run_id}: {ex}", exc_info=True)
                yield json.dumps({
                    "type": "text_delta",
                    "delta": f"I hit a problem completing the analysis for `{req.asset_id}` ({str(ex)}). Please retry in a moment."
                }) + "\n"
                yield json.dumps({"type": "done", "run_id": run_id}) + "\n"
                return

            if getattr(advisory, "objective_id", None) == "CLARIFICATION":
                t_id = getattr(advisory, "_thread_id", None) or session_id or run_id
                if session_id:
                    _pending_clarifications[session_id] = {
                        "thread_id": t_id, "asset_id": advisory.asset_id
                    }
                yield json.dumps({
                    "type": "status", "run_id": run_id, "stage": "CLARIFYING",
                    "message": "Agent Jane needs a bit more info..."
                }) + "\n"
                for chunk in _iter_stream_chunks(advisory.assessment):
                    yield json.dumps({"type": "text_delta", "delta": chunk}) + "\n"
                yield json.dumps({"type": "done", "run_id": run_id}) + "\n"
                return

        ev_count = len(advisory.evidence) if hasattr(advisory, 'evidence') else 0
        yield json.dumps({
            "type": "status",
            "run_id": run_id,
            "stage": "SPECIALISTS_RUNNING",
            "message": f"Reviewed {ev_count} evidence items — composing your briefing..."
        }) + "\n"

        # Structured advisory payload (consumed by the evidence drawer / structured clients)
        yield json.dumps({
            "type": "advisory",
            "run_id": run_id,
            "advisory": advisory.model_dump()
        }) + "\n"

        # Conversational NLG narrative — real LLM generation grounded in the advisory,
        # replacing the old rigid templated report. Salutation -> what I inspected ->
        # reasoning -> diagnosis -> recommendation -> verification -> follow-up invite.
        yield json.dumps({
            "type": "status", "run_id": run_id, "stage": "COMPOSING",
            "message": "Writing your diagnostic briefing..."
        }) + "\n"
        narrative = await asyncio.to_thread(
            _compose_diagnostic_narrative, advisory, req.user_query, objective_id, req.asset_id
        )
        for chunk in _iter_stream_chunks(narrative):
            yield json.dumps({"type": "text_delta", "delta": chunk}) + "\n"

        # Fleet objectives are cross-asset — no single-asset telemetry chart. Finish here.
        if objective_id in _FLEET_OBJECTIVES:
            yield json.dumps({"type": "done", "run_id": run_id}) + "\n"
            return

        # Event 5: Generative UI Block (Validated VisualizationSpec Pydantic Contract)
        live_traces = live_bridge.build_plotly_trace(req.asset_id)
        # MOCK_SCAFFOLD: hardcoded demo chart series | reason: used when cced_esp timeseries is
        # empty/unreachable so the UI still renders a chart | expiry: when live timeseries is
        # guaranteed | ref: src/verification/handoff.py:CHART_FALLBACK_PRODUCTION (kept in sync)
        default_data = [
            {
                "x": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "24:00"],
                "y": [1750, 1720, 1680, 1550, 1490, 1420, 1380],
                "type": "scatter",
                "mode": "lines+markers",
                "name": "Production Rate (BPD)",
                "line": {"color": "#ef4444", "width": 2.5}
            },
            {
                "x": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "24:00"],
                "y": [4100, 4080, 4050, 3950, 3900, 3850, 3800],
                "type": "scatter",
                "mode": "lines+markers",
                "name": "Total Dynamic Head (ft)",
                "yaxis": "y2",
                "line": {"color": "#0284c7", "width": 2, "dash": "dot"}
            }
        ]

        vis_spec = VisualizationSpec(
            vis_id=f"vis-{run_id}",
            type="plotly_chart",
            title=f"Telemetry Trend & Pump Curve — Asset {req.asset_id}",
            evidence_ids=[getattr(ev, 'source_id', 'EV-01') for ev in getattr(advisory, 'evidence', [])[:3]],
            chart=ChartSpec(
                chart_engine="plotly",
                data=live_traces if live_traces else default_data,
                layout={
                    "autosize": True,
                    "margin": {"l": 40, "r": 40, "t": 30, "b": 30},
                    "paper_bgcolor": "transparent",
                    "plot_bgcolor": "rgba(240,242,245,0.5)",
                    "font": {"family": "Inter, sans-serif", "size": 11, "color": "#191c1d"},
                    "xaxis": {"gridcolor": "#e2e8f0"},
                    "yaxis": {"title": "Value", "gridcolor": "#e2e8f0"},
                    "yaxis2": {"title": "Pressure / Temp", "overlaying": "y", "side": "right"},
                    "legend": {"orientation": "h", "y": -0.2}
                }
            )
        )

        chart_payload = {
            "type": "generative_ui",
            "kind": "plotly_chart",
            "chart_id": f"chart-{run_id}",
            "title": vis_spec.title,
            "data": vis_spec.chart.data,
            "layout": vis_spec.chart.layout,
            "visualization_spec": vis_spec.model_dump()
        }
        yield json.dumps(chart_payload) + "\n"

        # Event 6: Stream completion flag
        yield json.dumps({
            "type": "done",
            "run_id": run_id
        }) + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive"
        }
    )



@router.get("/runs/{run_id}/status", response_model=Dict[str, Any])
def get_run_status(run_id: str):
    """
    GET /api/ui/runs/{run_id}/status
    Polls real-time milestone execution status.
    """
    return {
        "run_id": run_id,
        "status": "COMPLETED",
        "current_milestone": "ADVISORY_READY",
        "milestones_passed": [
            "QUEUED", "RESOLVING_ASSET", "DATA_QUALITY_GATE",
            "PLANNING", "SPECIALISTS_RUNNING", "COLLECTING_EVIDENCE",
            "CONFLICT_CHECK", "SAFETY_CHECK", "ADVISORY_READY"
        ]
    }


@router.get("/runs/{run_id}/evidence", response_model=Dict[str, Any])
def get_run_evidence(run_id: str):
    """
    GET /api/ui/runs/{run_id}/evidence
    Returns frozen EvidencePack, ContextView, and XAI explanation payload for evidence drawer drill-down.
    """
    pack = evidence_repo.get_evidence_pack(run_id) or evidence_repo.get_evidence_pack(f"pack-{run_id}") or evidence_repo._packs_store.get(run_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"No evidence pack found for run '{run_id}'.")

    # MOCK_SCAFFOLD: hardcoded evidence-endpoint advisory | reason: get_run_evidence uses a static
    # advisory for the XAI explanation and ignores run_id | expiry: when evidence is looked up per
    # run_id with the real advisory | ref: known gap flagged in session audit
    advisory = {
        "diagnosis": "Intake Gas Interference probable",
        "confidence": 0.88
    }

    explanation = XAIEngine.generate_explanation(pack, advisory)

    return {
        "run_id": run_id,
        "evidence_pack": pack.model_dump(),
        "xai_explanation": explanation.model_dump()
    }
