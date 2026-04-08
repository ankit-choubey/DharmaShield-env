"""V4 endpoint tests: root, episodes, UI-safe server behavior."""

from fastapi.testclient import TestClient

from dharma_shield.server import app


def test_root_endpoint_returns_200():
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["openenv"] is True
    assert "tasks" in data
    assert len(data["tasks"]) >= 4


def test_episodes_endpoint_returns_200():
    client = TestClient(app)
    r = client.get("/episodes")
    assert r.status_code == 200
    data = r.json()
    assert "episodes" in data
    assert "total_logged" in data


def test_health_returns_correct_version():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["version"] == "3.1.0"
