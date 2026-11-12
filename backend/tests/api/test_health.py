from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert "provider" in data
    assert "synthetic_mode" in data
    assert "checks" in data
    assert data["checks"]["data_dir"] is True
    assert data["checks"]["fixtures"] is True


def test_health_503_when_data_dir_missing_or_unwritable(monkeypatch, tmp_path):
    blocked_path = tmp_path / "not_a_dir"
    blocked_path.write_text("file blocking dir creation")
    monkeypatch.setattr(settings, "DATA_DIR", str(blocked_path))

    response = client.get("/api/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["checks"]["data_dir"] is False
    assert data["checks"]["fixtures"] is False


def test_health_503_when_fixtures_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path))

    response = client.get("/api/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["checks"]["data_dir"] is True
    assert data["checks"]["fixtures"] is False

