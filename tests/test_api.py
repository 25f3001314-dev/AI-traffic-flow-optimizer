from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_preset_listing() -> None:
    response = client.get("/api/simulate/presets")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_run_simulation_endpoint() -> None:
    response = client.post("/api/simulate/run?preset_id=morning_peak")
    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_name"] == "Morning Peak"
    assert "improvements" in payload
