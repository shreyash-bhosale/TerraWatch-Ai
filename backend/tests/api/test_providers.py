import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.providers.mock_provider import MockProvider
from app.providers.local_provider import LocalProvider
from app.providers.nisar_provider import NisarProvider
from app.providers.registry import get_provider
from app.schemas.common import GeoJSONPolygonGeometry

client = TestClient(app)


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


def test_local_provider_missing_sidecar_warning(tmp_path: Path):
    # Create a tif without json sidecar
    tif = tmp_path / "orphan.tif"
    tif.write_bytes(b"fake tiff bytes")

    provider = LocalProvider(tmp_path)
    aoi = GeoJSONPolygonGeometry(
        type="Polygon",
        coordinates=[[[73.8, 18.4], [73.9, 18.4], [73.9, 18.5], [73.8, 18.5], [73.8, 18.4]]],
    )
    obs, warnings = provider.search(aoi)
    assert len(obs) == 0
    assert len(warnings) == 1
    assert "missing required sidecar" in warnings[0]


def test_local_provider_path_traversal_blocked(tmp_path: Path):
    # Create a sidecar referencing a file outside local_dir
    tif = tmp_path / "valid.tif"
    tif.write_bytes(b"fake tiff bytes")
    sidecar = tmp_path / "valid.json"
    sidecar.write_text(
        json.dumps(
            {
                "id": "evil_obs",
                "provider": "local",
                "synthetic": False,
                "acquisition_date": "2026-01-01T00:00:00Z",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[73.8, 18.4], [73.9, 18.4], [73.9, 18.5], [73.8, 18.5], [73.8, 18.4]]],
                },
                "asset_location": "../../etc/passwd",
                "asset_format": "GTiff",
            }
        )
    )
    provider = LocalProvider(tmp_path)
    with pytest.raises(PermissionError, match="Path traversal detected"):
        provider.list()

    with pytest.raises(PermissionError, match="Invalid observation ID"):
        provider.get("../secret")


def test_static_outputs_path_traversal_blocked():
    res = client.get("/files/outputs/..%2F..%2Fetc/passwd")
    assert res.status_code in (403, 404)
    res2 = client.get("/files/outputs/job123/..%2Fsecret.json")
    assert res2.status_code in (403, 404)

