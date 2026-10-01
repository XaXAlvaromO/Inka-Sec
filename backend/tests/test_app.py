from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_hello():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"