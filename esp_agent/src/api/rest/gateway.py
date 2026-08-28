"""
Unified FastAPI REST Gateway for ESP Agentic Platform
Grounded in ESP_APM_PHASE_5_FINAL_Service_Tool_MCP_Implementation_Design.docx §12, §14

Mounts:
- GET /health, /readiness, /version
- /api/v1/assets (AssetContextService)
- /api/v1/telemetry (TelemetryService)
- /api/v1/engineering (EngineeringService)
- /api/v1/twin (DigitalTwinService)
- /api/v1/cases (CaseOutcomeService)
- /api/v1/audit (AuditService)
"""

import uuid
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from shared.schemas.envelope import RESTEnvelope, ResponseMeta
from shared.schemas.errors import ServiceErrorPayload, ErrorDetail

from src.services.asset_context_service import AssetContextService
from src.services.telemetry_service import TelemetryService
from src.services.engineering_service import EngineeringService
from src.services.twin_service import DigitalTwinService
from src.services.case_service import CaseOutcomeService
from src.services.audit_service import AuditService
from src.policy.policy_engine import PolicyEngine

from shared.schemas.telemetry import IngestTelemetryRequest
from shared.schemas.engineering import TDHRequest, BEPRequest, DrawdownRequest
from shared.schemas.twin import FrequencyWhatIfRequest, WaterCutWhatIfRequest, OptimizationRequest
from shared.schemas.case import CaseSearchRequest, OutcomeCapturePayload
from shared.schemas.audit import AdvisoryAuditPayload, ToolCallAuditPayload

from src.api.rest.evidence_routes import router as evidence_router
from src.api.rest.bff_routes import router as bff_router
from src.mcp.rest_facade import router as mcp_router

app = FastAPI(
    title="ESP APM Application Services Gateway",
    version="1.0.0",
    description="Unified REST Gateway exposing versioned domain application services."
)

app.include_router(evidence_router)
app.include_router(bff_router)
app.include_router(mcp_router)

# Mount the native MCP server (streamable-HTTP) when the optional `mcp` package is present.
# The REST facade at /api/mcp always works; this adds an MCP-protocol endpoint at /mcp for
# MCP-native clients (Claude Desktop, Kiro, etc.). Gracefully skipped if `mcp` is unavailable.
try:
    from src.mcp.mcp_server import build_streamable_http_app
    _mcp_app = build_streamable_http_app()
    if _mcp_app is not None:
        app.mount("/mcp", _mcp_app)
except Exception as _mcp_exc:  # pragma: no cover - defensive, never block gateway startup
    import logging as _logging
    _logging.getLogger(__name__).warning("MCP native server not mounted: %s", _mcp_exc)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_llm_warmup():
    """Pre-warm LLM Gateway & Supervisor graph in background on server startup."""
    import asyncio
    def _warmup_background():
        try:
            from src.llm.adapter import LLMAdapter
            adapter = LLMAdapter()
            adapter.generate(prompt="warmup", run_id="WARMUP-STARTUP")
        except Exception:
            pass
    asyncio.create_task(asyncio.to_thread(_warmup_background))

# Instantiate Application Services & Policy Engine
asset_service = AssetContextService()
telemetry_service = TelemetryService()
engineering_service = EngineeringService()
twin_service = DigitalTwinService()
case_service = CaseOutcomeService()
audit_service = AuditService()
policy_engine = PolicyEngine()


# Global Tracing & Envelope Middleware
@app.middleware("http")
async def add_tracing_and_envelope_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", f"REQ-{uuid.uuid4().hex[:8]}")
    correlation_id = request.headers.get("X-Correlation-ID", f"CORR-{uuid.uuid4().hex[:8]}")
    tenant_id = request.headers.get("X-Tenant-ID", "CCED")

    request.state.request_id = request_id
    request.state.correlation_id = correlation_id
    request.state.tenant_id = tenant_id

    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Service-Version"] = "1.0.0"
    return response


# Health & Infrastructure Endpoints
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "esp_apm_gateway", "version": "1.0.0"}


@app.get("/readiness")
def readiness_check():
    return {"status": "ready", "services": {"asset": "ready", "telemetry": "ready", "engineering": "ready"}}


@app.get("/version")
def version_info():
    return {"platform": "ESP APM Service Platform", "api_version": "v1", "schema_version": "v2.1"}


# 12.1 Asset Context Service Endpoints
@app.get("/api/v1/assets", response_model=RESTEnvelope[List[str]])
def list_assets(request: Request):
    assets = asset_service.list_assets()
    return RESTEnvelope.success(
        data=assets,
        service="asset_context_service",
        request_id=request.state.request_id,
        correlation_id=request.state.correlation_id
    )


@app.get("/api/v1/assets/{asset_id}/context")
def get_asset_context(asset_id: str, request: Request):
    policy_engine.enforce_tenant_isolation(request.state.tenant_id, asset_id)
    try:
        ctx = asset_service.get_context(asset_id)
        return RESTEnvelope.success(
            data=ctx.model_dump(),
            service="asset_context_service",
            request_id=request.state.request_id,
            correlation_id=request.state.correlation_id
        )
    except ValueError as ex:
        err = ServiceErrorPayload.create("ASSET_NOT_FOUND", str(ex), target=asset_id)
        return JSONResponse(
            status_code=404,
            content=RESTEnvelope.error(err, service="asset_context_service", request_id=request.state.request_id).model_dump()
        )


@app.get("/api/v1/assets/{asset_id}/tags")
def get_asset_tags(asset_id: str, request: Request):
    try:
        mapping = asset_service.get_tag_mapping(asset_id)
        return RESTEnvelope.success(data=mapping, service="asset_context_service", request_id=request.state.request_id)
    except ValueError as ex:
        err = ServiceErrorPayload.create("ASSET_NOT_FOUND", str(ex), target=asset_id)
        return JSONResponse(status_code=404, content=RESTEnvelope.error(err, service="asset_context_service").model_dump())


# 12.2 Telemetry Endpoints
@app.get("/api/v1/telemetry/{asset_id}/latest")
def get_latest_telemetry(asset_id: str, request: Request):
    snap = telemetry_service.get_latest(asset_id)
    return RESTEnvelope.success(data=snap.model_dump(), service="telemetry_service", request_id=request.state.request_id)


@app.post("/api/v1/telemetry")
def ingest_telemetry(req: IngestTelemetryRequest, request: Request):
    res = telemetry_service.ingest_telemetry(req)
    return RESTEnvelope.success(data=res, service="telemetry_service", request_id=request.state.request_id)


# 12.3 Engineering Endpoints
@app.post("/api/v1/engineering/tdh")
def calculate_tdh(req: TDHRequest, request: Request):
    res = engineering_service.calculate_tdh(req)
    return RESTEnvelope.success(data=res.model_dump(), service="engineering_service", request_id=request.state.request_id)


@app.post("/api/v1/engineering/bep")
def calculate_bep(req: BEPRequest, request: Request):
    res = engineering_service.calculate_bep(req)
    return RESTEnvelope.success(data=res.model_dump(), service="engineering_service", request_id=request.state.request_id)


# 12.7 Digital Twin Endpoints
@app.post("/api/v1/twin/what-if/frequency")
def simulate_frequency_change(req: FrequencyWhatIfRequest, request: Request):
    res = twin_service.simulate_frequency_change(req)
    return RESTEnvelope.success(data=res.model_dump(), service="digital_twin_service", request_id=request.state.request_id)


@app.post("/api/v1/twin/optimize")
def optimize_speed(req: OptimizationRequest, request: Request):
    res = twin_service.optimize_vsd_speed(req)
    return RESTEnvelope.success(data=res.model_dump(), service="digital_twin_service", request_id=request.state.request_id)


# 12.6 Case & Outcome Endpoints
@app.post("/api/v1/cases/search")
def search_cases(req: CaseSearchRequest, request: Request):
    res = case_service.search_cases(req)
    return RESTEnvelope.success(data=res.model_dump(), service="case_outcome_service", request_id=request.state.request_id)


@app.get("/api/v1/cases/verification-checks")
def get_verification_checks(asset_id: str, request: Request):
    checks = case_service.get_verification_checks(asset_id)
    return RESTEnvelope.success(data=[c.model_dump() for c in checks], service="case_outcome_service", request_id=request.state.request_id)


@app.post("/api/v1/audit/outcome")
def capture_outcome(payload: OutcomeCapturePayload, request: Request):
    res = case_service.capture_outcome(payload)
    return RESTEnvelope.success(data=res, service="case_outcome_service", request_id=request.state.request_id)


# 12.8 Audit Endpoints
@app.post("/api/v1/audit/advisory")
def log_advisory(payload: AdvisoryAuditPayload, request: Request):
    res = audit_service.log_advisory(payload)
    return RESTEnvelope.success(data=res, service="audit_service", request_id=request.state.request_id)


@app.get("/api/v1/audit/{trace_id}")
def get_trace(trace_id: str, request: Request):
    trace = audit_service.get_execution_trace(trace_id)
    return RESTEnvelope.success(data=trace.model_dump(), service="audit_service", request_id=request.state.request_id)


# Phase 7 Supervisor Agent Endpoint
from pydantic import BaseModel, Field

class AgentRunRequest(BaseModel):
    user_query: str = Field(description="Natural language user query")
    asset_id: str = Field(description="Target ESP asset ID")

@app.post("/v1/agent/run")
def run_supervisor_agent(req: AgentRunRequest, request: Request):
    from src.agent.supervisor.user_entry import UserEntryAdapter
    adapter = UserEntryAdapter()
    advisory = adapter.run(
        user_query=req.user_query,
        asset_id=req.asset_id,
        request_id=request.state.request_id,
        tenant_id=request.state.tenant_id
    )
    return RESTEnvelope.success(
        data=advisory.model_dump(),
        service="supervisor_agent",
        request_id=request.state.request_id,
        correlation_id=request.state.correlation_id
    )
