import uuid
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.agent.runtime import DiagnosticAgentRuntime
from src.schemas.canonical import DiagnosticResult

app = FastAPI(
    title="Knowledge-Base-Agnostic Diagnostic Agent API",
    description="REST API for domain-agnostic industrial equipment diagnostic agent",
    version="1.0.0",
)

# Enable CORS for Next.js web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for registered knowledge bases and execution runs
REGISTERED_KNOWLEDGE_BASES: Dict[str, str] = {
    "esp": "knowledge_bases/esp"
}
DIAGNOSTIC_RUNS: Dict[str, Dict[str, Any]] = {}


class RegisterKBRequest(BaseModel):
    kb_id: str = Field(..., description="Unique ID for the knowledge base")
    kb_path: str = Field(..., description="Local path to knowledge base directory")


class DiagnoseRequest(BaseModel):
    user_query: str = Field(..., description="Diagnostic query or symptom description")
    asset_id: str = Field(..., description="ID of the target asset")
    kb_id: str = Field("esp", description="Knowledge base ID to use")


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "registered_kbs_count": len(REGISTERED_KNOWLEDGE_BASES),
        "total_runs_count": len(DIAGNOSTIC_RUNS),
    }


@app.get("/knowledge-bases")
def list_knowledge_bases():
    return {"registered_knowledge_bases": REGISTERED_KNOWLEDGE_BASES}


@app.post("/knowledge-bases/register")
def register_knowledge_base(req: RegisterKBRequest):
    REGISTERED_KNOWLEDGE_BASES[req.kb_id] = req.kb_path
    return {"status": "success", "kb_id": req.kb_id, "kb_path": req.kb_path}


@app.post("/diagnose")
def run_diagnosis(req: DiagnoseRequest):
    if req.kb_id not in REGISTERED_KNOWLEDGE_BASES:
        raise HTTPException(status_code=404, detail=f"Knowledge base '{req.kb_id}' not found.")

    kb_path = REGISTERED_KNOWLEDGE_BASES[req.kb_id]
    try:
        runtime = DiagnosticAgentRuntime(kb_path=kb_path)
        result: DiagnosticResult = runtime.run_diagnosis(
            user_query=req.user_query,
            asset_id=req.asset_id
        )
        run_id = str(uuid.uuid4())
        run_record = {
            "run_id": run_id,
            "user_query": req.user_query,
            "asset_id": req.asset_id,
            "kb_id": req.kb_id,
            "result": result.model_dump(),
        }
        DIAGNOSTIC_RUNS[run_id] = run_record
        return run_record
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/diagnose/{run_id}")
def get_diagnosis_result(run_id: str):
    if run_id not in DIAGNOSTIC_RUNS:
        raise HTTPException(status_code=404, detail=f"Run ID '{run_id}' not found.")
    return DIAGNOSTIC_RUNS[run_id]
