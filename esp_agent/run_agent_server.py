"""
ESP Agent Gateway Server — runs on port 8090.
Unified REST Gateway exposing Agent Jane BFF, Evidence Packs, and LangGraph Supervisor.
"""
import sys
import uvicorn
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    print("[AGENT GATEWAY] Starting ESP Agent Gateway at http://127.0.0.1:8090 ...", flush=True)
    uvicorn.run(
        "src.api.rest.gateway:app",
        host="0.0.0.0",
        port=8090,
        log_level="info",
        reload=True
    )
