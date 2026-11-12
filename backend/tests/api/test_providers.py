import json
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.providers.mock_provider import MockProvider
from app.providers.local_provider import LocalProvider
from app.providers.nisar_provider import NisarProvider
from app.providers.registry import get_provider
from app.schemas.common import GeoJSONPolygonGeometry

client = TestClient(app)

TEST_AOI = GeoJSONPolygonGeometry(
    type="Polygon",
    coordinates=[[[73.8, 18.4], [73.9, 18.4], [73.9, 18.5], [73.8, 18.5], [73.8, 18.4]]],
)


def _write_test_geotiff(path: Path) -> None:
    arr = np.full((8, 8), -12.0, dtype=np.float32)
    transform = from_bounds(73.75, 18.35, 73.95, 18.55, 8, 8)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=8,
        width=8,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(arr, 1)


def _sidecar_payload(obs_id: str, asset_location: str, acq_date: str = "2026-01-10T00:00:00Z") -> dict:
    return {
        "id": obs_id,
        "provider": "local",
        "synthetic": False,
        "acquisition_date": acq_date,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[73.75, 18.35], [73.95, 18.35], [73.95, 18.55], [73.75, 18.55], [73.75, 18.35]]],
        },
        "asset_location": asset_location,
        "asset_format": "GTiff",
        "polarization": "HH",
        "frequency_band": "L",
        "orbit_direction": "ascending",
        "measurement_units": "dB",
    }


def test_nisar_provider_stub_raises_blocked():
    with pytest.raises(NotImplementedError, match="BLOCKED: awaiting official NISAR resources"):
        NisarProvider()


def test_registry_nisar_raises_blocked(monkeypatch):
    monkeypatch.setattr(settings, "PROVIDER", "nisar")
    with pytest.raises(NotImplementedError, match="BLOCKED: awaiting official NISAR resources"):
        get_provider()


def test_registry_unknown_provider_raises(monkeypatch):
    monkeypatch.setattr(settings, "PROVIDER", "unknown_sat")
    with pytest.raises(ValueError, match="Unknown PROVIDER"):
        get_provider()


def test_local_provider_valid_asset_search_list_get_and_open_asset(tmp_path: Path):
    tif_a = tmp_path / "scene_a.tif"
    tif_b = tmp_path / "scene_b.tif"
    _write_test_geotiff(tif_a)
    _write_test_geotiff(tif_b)

    (tmp_path / "scene_a.json").write_text(json.dumps(_sidecar_payload("loc_a", "scene_a.tif", "2026-01-05T00:00:00Z")))
    (tmp_path / "scene_b.json").write_text(json.dumps(_sidecar_payload("loc_b", "scene_b.tif", "2026-01-20T00:00:00Z")))

    # Non-raster file should be ignored silently
    (tmp_path / "README.txt").write_text("notes")

    provider = LocalProvider(tmp_path)

    all_obs, total = provider.list(limit=1, offset=1)
    assert total == 2
    assert len(all_obs) == 1
    assert all_obs[0].id == "loc_b"

    filtered, warnings = provider.search(TEST_AOI, start_date="2026-01-01", end_date="2026-01-10")
    assert warnings == []
    assert [o.id for o in filtered] == ["loc_a"]

    obs = provider.get("loc_a")
    assert obs.id == "loc_a"
    assert provider.open_asset("loc_a") == tif_a.resolve()


def test_local_provider_handles_missing_dir_invalid_metadata_and_missing_asset(tmp_path: Path):
    # Non-existent local_dir yields empty catalog without crashing
    missing_provider = LocalProvider(tmp_path / "does_not_exist")
    assert missing_provider.list() == ([], 0)
    assert missing_provider.search(TEST_AOI) == ([], [])

    # Orphan raster without sidecar -> warning
    (tmp_path / "orphan.tif").write_bytes(b"fake tiff bytes")

    # Malformed JSON sidecar -> warning & skipped
    _write_test_geotiff(tmp_path / "bad_json.tif")
    (tmp_path / "bad_json.json").write_text("{not valid json")

    # Missing required fields / Pydantic schema error -> warning & skipped
    _write_test_geotiff(tmp_path / "bad_schema.tif")
    (tmp_path / "bad_schema.json").write_text(json.dumps({"id": "incomplete"}))

    # Sidecar pointing to non-existent asset file -> warning & skipped in scan
    _write_test_geotiff(tmp_path / "missing_target.tif")
    (tmp_path / "missing_target.json").write_text(
        json.dumps(_sidecar_payload("obs_missing_file", "nonexistent_asset.tif"))
    )

    provider = LocalProvider(tmp_path)
    obs, warnings = provider.search(TEST_AOI)
    assert obs == []
    assert len(warnings) == 4
    assert any("missing required sidecar" in w for w in warnings)
    assert any("Invalid sidecar for raster 'bad_json.tif'" in w for w in warnings)
    assert any("Invalid sidecar for raster 'bad_schema.tif'" in w for w in warnings)
    assert any("Referenced asset 'nonexistent_asset.tif' does not exist" in w for w in warnings)

    with pytest.raises(KeyError, match="not found in local provider"):
        provider.get("obs_missing_file")


def test_local_provider_path_traversal_blocked(tmp_path: Path):
    tif = tmp_path / "valid.tif"
    _write_test_geotiff(tif)
    sidecar = tmp_path / "valid.json"
    sidecar.write_text(json.dumps(_sidecar_payload("evil_obs", "../../etc/passwd")))

    provider = LocalProvider(tmp_path)
    with pytest.raises(PermissionError, match="Path traversal detected"):
        provider.list()

    with pytest.raises(PermissionError, match="Invalid observation ID"):
        provider.get("../secret")


def test_mock_provider_lookup_and_error_cases(tmp_path: Path):
    provider = MockProvider(settings.synthetic_data_path)
    listed, total = provider.list()
    assert total >= 2
    obs = provider.get("syn_before")
    assert obs.synthetic is True
    assert provider.open_asset("syn_before").is_file()

    with pytest.raises(KeyError, match="not found"):
        provider.get("nonexistent_obs_id")
    with pytest.raises(KeyError, match="not found"):
        provider.get("../syn_before")

    # Test traversal and missing-file guards in open_asset via an isolated temporary catalog
    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    (catalog_dir / "evil_mock.json").write_text(
        json.dumps(_sidecar_payload("evil_mock", "../../etc/passwd"))
    )
    (catalog_dir / "missing_mock.json").write_text(
        json.dumps(_sidecar_payload("missing_mock", "does_not_exist.tif"))
    )
    isolated_provider = MockProvider(catalog_dir)
    assert isolated_provider.get("evil_mock").synthetic is True  # Rule R3 always enforced
    with pytest.raises(PermissionError, match="Path traversal detected"):
        isolated_provider.open_asset("evil_mock")
    with pytest.raises(FileNotFoundError, match="not found"):
        isolated_provider.open_asset("missing_mock")


def test_static_outputs_path_traversal_blocked():
    # Single-segment '..' hits the route handler directly and returns 403 INVALID_REQUEST
    res_job = client.get("/files/outputs/..job/difference.tif")
    assert res_job.status_code == 403
    assert res_job.json()["error"]["code"] == "INVALID_REQUEST"

    res_file = client.get("/files/outputs/job123/..secret.json")
    assert res_file.status_code == 403
    assert res_file.json()["error"]["code"] == "INVALID_REQUEST"

    # Multi-segment traversal is also rejected before serving any file
    res_multi = client.get("/files/outputs/..%2F..%2Fetc/passwd")
    assert res_multi.status_code in (403, 404)
