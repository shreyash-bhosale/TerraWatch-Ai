import json
from pathlib import Path

import numpy as np
import pytest
import rasterio


def test_fixtures_exist_and_match_spec():
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    fixtures_dir = repo_root / "data" / "synthetic"

    # Files must exist
    assert (fixtures_dir / "syn_before.tif").is_file()
    assert (fixtures_dir / "syn_before.json").is_file()
    assert (fixtures_dir / "syn_after.tif").is_file()
    assert (fixtures_dir / "syn_after.json").is_file()
    assert (fixtures_dir / "syn_misaligned.tif").is_file()
    assert (fixtures_dir / "syn_wrongunits.tif").is_file()
    assert (fixtures_dir / "aoi.geojson").is_file()
    assert (fixtures_dir / "expected_stats.json").is_file()

    # Read syn_before
    with rasterio.open(fixtures_dir / "syn_before.tif") as src:
        arr_before = src.read(1)
        assert src.shape == (64, 64)
        assert src.crs.to_string() == "EPSG:4326"
        assert src.res == pytest.approx((0.001, 0.001))
        assert src.nodata == -9999.0
        # Rows 0-3, Cols 0-3 must be nodata
        assert np.all(arr_before[0:4, 0:4] == -9999.0)
        # Other pixels must be -15.0
        mask_valid = arr_before != -9999.0
        assert np.all(arr_before[mask_valid] == -15.0)

    # Read syn_after
    with rasterio.open(fixtures_dir / "syn_after.tif") as src:
        arr_after = src.read(1)
        assert src.shape == (64, 64)
        assert src.nodata == -9999.0
        # Rows 60-63, Cols 60-63 must be nodata
        assert np.all(arr_after[60:64, 60:64] == -9999.0)
        # Rows 20-39, Cols 20-39 must be -22.0
        assert np.all(arr_after[20:40, 20:40] == -22.0)

    # Compute difference on valid pixels
    valid_mask = (arr_before != -9999.0) & (arr_after != -9999.0)
    diff = arr_after[valid_mask] - arr_before[valid_mask]

    # Load expected stats
    with open(fixtures_dir / "expected_stats.json") as f:
        expected = json.load(f)

    assert len(diff) == expected["valid_pixel_count"] == 4064
    assert np.count_nonzero(~valid_mask) == expected["invalid_pixel_count"] == 32
    assert float(np.mean(diff)) == pytest.approx(expected["mean"], rel=1e-5)
    assert float(np.median(diff)) == pytest.approx(expected["median"], abs=1e-5)
    assert float(np.min(diff)) == pytest.approx(expected["min"], abs=1e-5)
    assert float(np.max(diff)) == pytest.approx(expected["max"], abs=1e-5)
    assert float(np.std(diff)) == pytest.approx(expected["std"], rel=1e-5)
