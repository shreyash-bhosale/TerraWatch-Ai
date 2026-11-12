import json
from pathlib import Path
import numpy as np
import pytest
from app.processing.readers.geotiff import GeoTIFFReader
from app.processing.preprocessing import (
    crop_to_aoi,
    compute_aoi_window,
    mask_nodata_to_nan,
    EmptyWindowError,
    NoValidPixelsError,
)

def test_crop_to_aoi_valid():
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    reader = GeoTIFFReader()
    raster = reader.read(fixtures_dir / "syn_after.tif")

    # Bounding polygon covering center 20x20
    aoi = {
        "type": "Polygon",
        "coordinates": [
            [
                [73.820, 18.520],
                [73.840, 18.520],
                [73.840, 18.540],
                [73.820, 18.540],
                [73.820, 18.520],
            ]
        ],
    }

    cropped = crop_to_aoi(raster, aoi)
    assert cropped.shape[0] > 0
    assert cropped.shape[1] > 0
    assert np.count_nonzero(~np.isnan(cropped.array)) > 0

def test_crop_to_disjoint_aoi_raises_empty():
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    reader = GeoTIFFReader()
    raster = reader.read(fixtures_dir / "syn_after.tif")

    disjoint_aoi = {
        "type": "Polygon",
        "coordinates": [
            [
                [80.0, 30.0],
                [81.0, 30.0],
                [81.0, 31.0],
                [80.0, 31.0],
                [80.0, 30.0],
            ]
        ],
    }

    with pytest.raises(EmptyWindowError):
        crop_to_aoi(raster, disjoint_aoi)

def test_crop_to_only_nodata_region_raises_no_valid_pixels():
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    reader = GeoTIFFReader()
    raster = reader.read(fixtures_dir / "syn_before.tif")

    # In syn_before, rows 0-3, cols 0-3 are nodata.
    # Origin is (73.800, 18.560), pixel_size = 0.001.
    # Cols 0-3: 73.800 to 73.803. Rows 0-3: 18.560 down to 18.557.
    nodata_aoi = {
        "type": "Polygon",
        "coordinates": [
            [
                [73.8001, 18.5571],
                [73.8029, 18.5571],
                [73.8029, 18.5599],
                [73.8001, 18.5599],
                [73.8001, 18.5571],
            ]
        ],
    }

    with pytest.raises(NoValidPixelsError):
        crop_to_aoi(raster, nodata_aoi)
