import json
from pathlib import Path

import numpy as np
import pytest

from app.processing.change_detection import difference_db
from app.processing.readers.geotiff import GeoTIFFReader
from app.processing.statistics import compute_stats


def test_statistics_exact_match_with_expected():
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    reader = GeoTIFFReader()
    before = reader.read(fixtures_dir / "syn_before.tif")
    after = reader.read(fixtures_dir / "syn_after.tif")

    diff = difference_db(before, after)
    stats = compute_stats(diff, nodata=before.nodata)

    with open(fixtures_dir / "expected_stats.json", "r") as f:
        expected = json.load(f)

    assert stats["valid_pixel_count"] == expected["valid_pixel_count"] == 4064
    assert stats["invalid_pixel_count"] == expected["invalid_pixel_count"] == 32
    assert stats["total_pixel_count"] == expected["total_pixel_count"] == 4096
    assert stats["mean"] == pytest.approx(expected["mean"], rel=1e-6)
    assert stats["median"] == pytest.approx(expected["median"], abs=1e-6)
    assert stats["min"] == pytest.approx(expected["min"], abs=1e-6)
    assert stats["max"] == pytest.approx(expected["max"], abs=1e-6)
    assert stats["std"] == pytest.approx(expected["std"], rel=1e-6)

def test_statistics_all_nan():
    empty_arr = np.full((10, 10), np.nan, dtype=np.float32)
    stats = compute_stats(empty_arr)
    assert stats["valid_pixel_count"] == 0
    assert stats["invalid_pixel_count"] == 100
    assert stats["total_pixel_count"] == 100
    assert np.isnan(stats["mean"])
    assert np.isnan(stats["median"])
