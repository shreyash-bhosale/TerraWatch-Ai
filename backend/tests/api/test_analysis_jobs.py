import json
import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.job_manager import job_manager

client = TestClient(app)

SAMPLE_AOI = {
    "type": "Polygon",
    "coordinates": [
        [
            [73.8, 18.496],
            [73.864, 18.496],
            [73.864, 18.56],
            [73.8, 18.56],
            [73.8, 18.496],
        ]
    ],
}


def test_create_and_run_analysis_job():
    payload = {
        "before_id": "syn_before",
        "after_id": "syn_after",
        "aoi": SAMPLE_AOI,
    }
    # 1. Create Job (202 Accepted)
    response = client.post("/api/analysis", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    job_id = data["job_id"]

    # 2. Poll until completed or timeout
    max_wait = 10.0
    start_time = time.time()
    final_status = None

    while time.time() - start_time < max_wait:
        poll_resp = client.get(f"/api/analysis/{job_id}")
        assert poll_resp.status_code == 200
        poll_data = poll_resp.json()
        assert poll_data["job_id"] == job_id
        assert poll_data["before_id"] == "syn_before"
        assert poll_data["after_id"] == "syn_after"
        assert poll_data["synthetic"] is True
        assert poll_data["stage"] in [
            "queued",
            "validating",
            "reading",
            "aligning",
            "differencing",
            "statistics",
            "exporting",
            "completed",
            "failed",
        ]

        if poll_data["status"] in ("completed", "failed"):
            final_status = poll_data
            break
        time.sleep(0.2)

    assert final_status is not None, "Job timed out"
    assert final_status["status"] == "completed"
    assert final_status["stage"] == "completed"
    assert final_status["finished_at"] is not None

    # 3. Retrieve Results (200 OK)
    res_resp = client.get(f"/api/analysis/{job_id}/results")
    assert res_resp.status_code == 200
    res = res_resp.json()
    assert "statistics" in res
    stats = res["statistics"]
    assert stats["valid_pixel_count"] > 0
    assert stats["total_pixel_count"] > 0
    assert stats["min"] <= stats["max"]
    assert "bounds" in res
    assert len(res["bounds"]) == 4
    assert res["synthetic"] is True

    # Check limitations text
    assert "limitations" in res
    assert any("DEMO DATA — SYNTHETIC" in lim for lim in res["limitations"])

    # 4. Check layer URLs and file serving
    layers = res["layers"]
    assert "difference_png" in layers
    assert "before_png" in layers
    assert "after_png" in layers

    diff_png_resp = client.get(layers["difference_png"])
    assert diff_png_resp.status_code == 200
    assert diff_png_resp.headers["content-type"] == "image/png"

    geotiff_resp = client.get(res["geotiff_url"])
    assert geotiff_resp.status_code == 200
    assert geotiff_resp.headers["content-type"] == "image/tiff"


def test_get_results_conflict_when_not_completed():
    # Insert a dummy job record directly in queued status
    dummy_id = "job_test_not_completed"
    job_record = {
        "job_id": dummy_id,
        "status": "running",
        "stage": "reading",
        "created_at": "2026-01-01T00:00:00Z",
        "started_at": "2026-01-01T00:00:01Z",
        "finished_at": None,
        "before_id": "syn_before",
        "after_id": "syn_after",
        "aoi": SAMPLE_AOI,
        "synthetic": True,
        "error": None,
        "result_dir": f"/tmp/{dummy_id}",
    }
    job_manager._atomic_write_job(job_record)

    response = client.get(f"/api/analysis/{dummy_id}/results")
    assert response.status_code == 409
    err = response.json()
    assert err["error"]["code"] == "JOB_NOT_COMPLETED"


def test_create_job_incompatible_rejected():
    payload = {
        "before_id": "syn_before",
        "after_id": "syn_wrongunits",
        "aoi": SAMPLE_AOI,
    }
    response = client.post("/api/analysis", json=payload)
    assert response.status_code == 422
    err = response.json()
    assert err["error"]["code"] == "INCOMPATIBLE_OBSERVATIONS"


def test_job_not_found():
    response = client.get("/api/analysis/job_does_not_exist_404")
    assert response.status_code == 404
    err = response.json()
    assert err["error"]["code"] == "JOB_NOT_FOUND"

    res_resp = client.get("/api/analysis/job_does_not_exist_404/results")
    assert res_resp.status_code == 404
    err = res_resp.json()
    assert err["error"]["code"] == "JOB_NOT_FOUND"


def test_job_fails_on_corrupt_raster(tmp_path, monkeypatch):
    from pathlib import Path
    from app.providers.mock_provider import MockProvider

    # Copy valid synthetic JSONs + write a corrupt TIFF for syn_after
    corrupt_dir = tmp_path / "corrupt_syn"
    corrupt_dir.mkdir()
    orig_dir = Path("data/synthetic")
    for fname in ["syn_before.tif", "syn_before.json", "syn_after.json"]:
        (corrupt_dir / fname).write_bytes((orig_dir / fname).read_bytes())
    (corrupt_dir / "syn_after.tif").write_bytes(b"CORRUPT_NOT_A_GEOTIFF")

    fake_provider = MockProvider(corrupt_dir)
    monkeypatch.setattr("app.api.analysis.get_provider", lambda: fake_provider)

    resp = client.post(
        "/api/analysis",
        json={"before_id": "syn_before", "after_id": "syn_after", "aoi": SAMPLE_AOI},
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    # Poll until failed
    final_status = None
    for _ in range(25):
        poll = client.get(f"/api/analysis/{job_id}").json()
        if poll["status"] in ("completed", "failed"):
            final_status = poll
            break
        time.sleep(0.1)

    assert final_status is not None
    assert final_status["status"] == "failed"
    assert final_status["stage"] == "failed"
    assert final_status["error"] is not None
    assert final_status["error"]["code"]

    # Results endpoint must return 409 JOB_NOT_COMPLETED
    res_resp = client.get(f"/api/analysis/{job_id}/results")
    assert res_resp.status_code == 409
