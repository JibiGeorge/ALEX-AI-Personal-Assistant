import pytest
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(data_dir=tmp_path, api_token="test-secret-token")
    return TestClient(app)


def test_voice_routes_lifecycle(client):
    headers = {"Authorization": "Bearer test-secret-token"}

    # 1. Get state
    resp = client.get("/api/v1/voice/state", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "state" in data
    assert "wake_word_enabled" in data

    # 2. Wake
    resp = client.post("/api/v1/voice/wake", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["state"] == "LISTENING"

    # 3. Interrupt
    resp = client.post("/api/v1/voice/interrupt", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # 4. Sleep
    resp = client.post("/api/v1/voice/sleep", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["state"] == "SLEEPING"

    # 5. Toggle wake word
    resp = client.post("/api/v1/voice/toggle-wake-word", json={"enabled": False}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["wake_word_enabled"] is False

