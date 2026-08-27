from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
def test_context():
    r=c.get("/api/v1/assets/FS-031/context"); assert r.status_code==200
    assert r.json()["asset_id"]=="FS-031"
def test_telemetry():
    p={"asset_id":"FS-031","timestamp":"2026-08-26T04:54:33.739Z","scenario":"normal","state":"running","values":{"liquid_rate_bpd":735.7}}
    assert c.post("/api/v1/telemetry",json=p).status_code==200
    assert c.get("/api/v1/assets/FS-031/telemetry/latest").json()["data"]["values"]["liquid_rate_bpd"]==735.7
