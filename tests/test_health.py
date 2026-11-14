# ReturnDesk - health endpoint tests
# Author: stephenoke14 | mrhills

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200_and_expected_keys() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"status", "database", "version", "environment"}
    assert body["status"] in {"ok", "degraded"}
