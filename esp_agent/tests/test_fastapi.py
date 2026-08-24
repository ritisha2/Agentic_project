from fastapi.testclient import TestClient
from src.api.fastapi_app import app

client = TestClient(app)


def test_fastapi_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"


def test_fastapi_knowledge_bases():
    res = client.get("/knowledge-bases")
    assert res.status_code == 200
    data = res.json()
    assert "esp" in data["registered_knowledge_bases"]


def test_fastapi_diagnose():
    payload = {
        "user_query": "ESP-Well-001 motor temperature is 140°C",
        "asset_id": "ESP-Well-001",
        "kb_id": "esp"
    }
    res = client.post("/diagnose", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "run_id" in data
    assert data["result"]["severity_level"] == "warning"
    assert "overheating" in data["result"]["identified_fault"].lower()

    # Retrieve run by ID
    run_id = data["run_id"]
    res_get = client.get(f"/diagnose/{run_id}")
    assert res_get.status_code == 200
    assert res_get.json()["run_id"] == run_id
