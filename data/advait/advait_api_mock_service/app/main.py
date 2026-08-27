from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .models import TelemetryPoint
from .store import store

app=FastAPI(title="ADVAIT Asset API Mock", version="v1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def asset_or_404(aid):
    a=store.get_asset(aid)
    if not a: raise HTTPException(404, f"Unknown asset_id: {aid}")
    return a

@app.get("/health")
def health(): return {"status":"ok","assets":len(store.assets)}

@app.get("/api/v1/assets")
def list_assets(): return {"items":store.list_assets(),"count":len(store.assets)}

@app.get("/api/v1/assets/{asset_id}")
def get_asset(asset_id): return asset_or_404(asset_id)

@app.get("/api/v1/assets/{asset_id}/context")
def get_context(asset_id):
    a=asset_or_404(asset_id)
    return {k:a[k] for k in ["asset_id","well_id","hierarchy","plant_context","well_context","esp_configuration","tag_mapping","signal_catalog","operating_envelope","source_provenance","missing_fields"]}

@app.get("/api/v1/assets/{asset_id}/tags")
def get_tags(asset_id):
    a=asset_or_404(asset_id)
    return {"asset_id":asset_id,"mapping_version":a["tag_mapping"]["mapping_version"],"tags":a["tag_mapping"]["tags"]}

@app.get("/api/v1/assets/{asset_id}/fault-catalog")
def get_faults(asset_id):
    a=asset_or_404(asset_id)
    return {"asset_id":asset_id,"catalog_version":a["fault_context"]["simulator_fault_catalog_version"],"items":a["fault_context"]["available_scenarios"]}

@app.patch("/api/v1/assets/{asset_id}")
def patch_asset(asset_id, patch: dict):
    a=store.patch(asset_id, patch)
    if not a: raise HTTPException(404, "Unknown asset")
    return a

@app.post("/api/v1/telemetry")
def ingest(p: TelemetryPoint):
    asset_or_404(p.asset_id); store.add_telemetry(p)
    return {"accepted":True,"asset_id":p.asset_id,"timestamp":p.timestamp}

@app.get("/api/v1/assets/{asset_id}/telemetry/latest")
def latest(asset_id):
    asset_or_404(asset_id); p=store.latest(asset_id)
    return {"asset_id":asset_id,"data":p}

@app.get("/api/v1/assets/{asset_id}/telemetry/history")
def history(asset_id, limit:int=Query(100, ge=1, le=5000)):
    asset_or_404(asset_id); return {"asset_id":asset_id,"items":store.history(asset_id,limit)}

@app.get("/api/v1/assets/{asset_id}/snapshot")
def snapshot(asset_id):
    a=asset_or_404(asset_id)
    return {"asset":a,"latest_telemetry":store.latest(asset_id),"retrieved_at":datetime.now(timezone.utc)}
