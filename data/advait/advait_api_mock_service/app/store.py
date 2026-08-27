import json
from datetime import datetime, timezone
from .config import DATA_FILE
from .models import TelemetryPoint

class Store:
    def __init__(self):
        data=json.loads(DATA_FILE.read_text())
        self.assets={a["asset_id"]:a for a in data["assets"]}
        self.telemetry={}
    def get_asset(self, asset_id): return self.assets.get(asset_id)
    def list_assets(self): return list(self.assets.values())
    def add_telemetry(self, p):
        self.telemetry.setdefault(p.asset_id, []).append(p)
        self.telemetry[p.asset_id]=self.telemetry[p.asset_id][-5000:]
    def latest(self, aid):
        return self.telemetry.get(aid, [])[-1] if self.telemetry.get(aid) else None
    def history(self, aid, limit): return self.telemetry.get(aid, [])[-limit:]
    def patch(self, aid, patch):
        a=self.assets.get(aid)
        if not a: return None
        for k,v in patch.items():
            if v is None: continue
            if k=="plant_section": a["plant_context"]["section"]=v
            elif k=="pump_model": a["esp_configuration"]["pump"]["model"]=v
            elif k=="pump_stage_count": a["esp_configuration"]["pump"]["stage_count"]=v
            elif k=="pump_curve_id": a["esp_configuration"]["pump"]["pump_curve_id"]=v
            elif k=="motor_model": a["esp_configuration"]["motor"]["model"]=v
            elif k=="vsd_model": a["esp_configuration"]["vsd"]["model"]=v
            elif k=="approved_limits": a["operating_envelope"]["approved_limits"]=v
            elif k=="asset_status": a["asset_status"]=v
        a["source_provenance"]["record_version"] += 1
        a["source_provenance"]["last_synced_at"]=datetime.now(timezone.utc).isoformat()
        return a
store=Store()
