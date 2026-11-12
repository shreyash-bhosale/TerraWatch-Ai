import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)

VALID_AOI = {
    "type": "Polygon",
    "coordinates": [[[73.80, 18.45], [73.95, 18.45], [73.95, 18.60], [73.80, 18.60], [73.80, 18.45]]],
}


def _assert_error_envelope(body: dict, expected_code: str | None = None):
    assert "error" in body
    err = body["error"]
    assert set(err.keys()) >= {"code", "message", "details"}
    assert isinstance(err["code"], str) and err["code"]
    assert isinstance(err["message"], str) and err["message"]
    if expected_code is not None:
        assert err["code"] == expected_code


def test_malformed_json_returns_error_envelope():
    res = client.post(
        "/api/observations/search",
        content=b"{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 422
    body = res.json()
    _assert_error_envelope(body, "INVALID_REQUEST")
    assert isinstance(body["error"]["details"], list) and len(body["error"]["details"]) >= 1


def test_wrong_field_type_returns_validation_details():
    res = client.post(
        "/api/analysis/validate",
        json={"before_id": "syn_before", "after_id": "syn_after", "aoi": "not-a-polygon"},
    )
    assert res.status_code == 422
    body = res.json()
    _assert_error_envelope(body, "INVALID_REQUEST")
    assert isinstance(body["error"]["details"], list) and len(body["error"]["details"]) >= 1


def test_oversize_request_body_returns_413_envelope(monkeypatch):
    monkeypatch.setattr(settings, "MAX_BODY_BYTES", 512)
    payload = {"aoi": VALID_AOI, "start_date": "x" * 1024}
    res = client.post("/api/observations/search", json=payload)
    assert res.status_code == 413
    _assert_error_envelope(res.json(), "INVALID_REQUEST")


def test_unknown_route_returns_error_envelope():
    res = client.get("/api/nonexistent-endpoint")
    assert res.status_code == 404
    _assert_error_envelope(res.json(), "INVALID_REQUEST")


def test_unhandled_exception_returns_500_without_stacktrace(monkeypatch):
    def boom(_job_id: str):
        raise RuntimeError("sensitive /var/lib/secret failure")

    monkeypatch.setattr("app.api.analysis.job_manager.get_status_response", boom)
    no_raise_client = TestClient(app, raise_server_exceptions=False)
    res = no_raise_client.get("/api/analysis/any_job_id")
    assert res.status_code == 500
    body = res.json()
    _assert_error_envelope(body, "INTERNAL_ERROR")
    assert "Traceback" not in res.text
    assert "/var/lib/secret" not in res.text


def test_provider_not_implemented_maps_to_503_everywhere(monkeypatch):
    monkeypatch.setattr(settings, "PROVIDER", "nisar")

    endpoints = [
        ("POST", "/api/observations/search", {"aoi": VALID_AOI}),
        ("GET", "/api/observations", None),
        ("GET", "/api/observations/syn_before", None),
        ("POST", "/api/analysis/validate", {"before_id": "syn_before", "after_id": "syn_after", "aoi": VALID_AOI}),
        ("POST", "/api/analysis", {"before_id": "syn_before", "after_id": "syn_after", "aoi": VALID_AOI}),
    ]
    for method, path, payload in endpoints:
        res = client.request(method, path, json=payload)
        assert res.status_code == 503, f"Expected 503 for {method} {path}, got {res.status_code}: {res.text}"
        _assert_error_envelope(res.json(), "PROVIDER_NOT_AVAILABLE")


def test_path_traversal_and_absolute_paths_safe_envelope(monkeypatch, tmp_path: Path):
    # Static outputs route traversal (.. and backslash / slash)
    for bad_path in [
        "/files/outputs/job123/..%5Csecret.json",
        "/files/outputs/..%5Cetc/passwd",
        "/files/outputs/..%2F..%2Fetc/passwd",
        "/files/outputs/job123/%2Fetc%2Fpasswd",
    ]:
        res = client.get(bad_path)
        assert res.status_code in (403, 404), f"Expected 403/404 for {bad_path}, got {res.status_code}"
        body = res.json()
        _assert_error_envelope(body, "INVALID_REQUEST")
        assert str(tmp_path) not in body["error"]["message"]
        assert "/Users" not in body["error"]["message"]

    # Local provider traversal via observation ID (both ../ and /abs/path) & sidecar asset_location
    local_dir = tmp_path / "local_sar"
    local_dir.mkdir()
    (local_dir / "obs.tif").write_bytes(b"fake")
    (local_dir / "obs.json").write_text(
        json.dumps(
            {
                "id": "abs_evil",
                "provider": "local",
                "synthetic": False,
                "acquisition_date": "2026-01-01T00:00:00Z",
                "geometry": VALID_AOI,
                "asset_location": "/etc/passwd",
                "asset_format": "GTiff",
            }
        )
    )
    monkeypatch.setattr(settings, "PROVIDER", "local")
    monkeypatch.setattr(settings, "LOCAL_DATA_DIR", str(local_dir))

    res_rel = client.get("/api/observations/..%5Csecret")
    assert res_rel.status_code == 403
    _assert_error_envelope(res_rel.json(), "INVALID_REQUEST")

    res_abs_id = client.post(
        "/api/analysis/validate",
        json={"before_id": "/etc/passwd", "after_id": "../secret", "aoi": VALID_AOI},
    )
    assert res_abs_id.status_code == 403
    _assert_error_envelope(res_abs_id.json(), "INVALID_REQUEST")

    res_list = client.get("/api/observations")
    assert res_list.status_code == 403
    body_list = res_list.json()
    _assert_error_envelope(body_list, "INVALID_REQUEST")
    assert str(local_dir) not in body_list["error"]["message"]
