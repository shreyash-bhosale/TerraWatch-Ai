import json
from pathlib import Path
import numpy as np
import pytest
from rasterio.crs import CRS
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds
from app.processing.raster_data import RasterData
from app.processing.readers.geotiff import GeoTIFFReader
from app.processing.preprocessing import (
    AoiTransformError,
    crop_to_aoi,
    compute_aoi_window,
    mask_nodata_to_nan,
    EmptyWindowError,
    NoValidPixelsError,
)
from app.processing.validation import validate_compatibility
from app.schemas.observation import Observation

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


def test_crop_to_aoi_projected_crs_epsg32643():
    # UTM Zone 43N raster around Pune (pixel size = 100 m, 60x60 grid = 6 km x 6 km)
    crs_utm = CRS.from_epsg(32643)
    origin_x, origin_y = 373000.0, 2052000.0
    pixel_size = 100.0
    transform = from_origin(origin_x, origin_y, pixel_size, pixel_size)
    bounds = (origin_x, origin_y - 60 * pixel_size, origin_x + 60 * pixel_size, origin_y)

    arr = np.full((60, 60), -14.0, dtype=np.float32)
    arr[0:2, :] = -9999.0  # top nodata strip
    raster = RasterData(
        array=arr,
        transform=transform,
        crs=crs_utm,
        nodata=-9999.0,
        bounds=bounds,
        resolution=(pixel_size, pixel_size),
        units="dB",
    )

    # Interior UTM box transformed into EPSG:4326 API AOI polygon (rows 10..30, cols 10..30)
    sub_bounds_utm = (origin_x + 1000.0, origin_y - 3000.0, origin_x + 3000.0, origin_y - 1000.0)
    w, s, e, n = transform_bounds(crs_utm, CRS.from_epsg(4326), *sub_bounds_utm)
    aoi_wgs84 = {
        "type": "Polygon",
        "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
    }

    win = compute_aoi_window(
        aoi_geometry=aoi_wgs84,
        raster_bounds=raster.bounds,
        transform=raster.transform,
        width=raster.width,
        height=raster.height,
        raster_crs=raster.crs,
    )
    assert win.col_off >= 9 and win.row_off >= 9
    assert win.width < 60 and win.height < 60

    cropped = crop_to_aoi(raster, aoi_wgs84)
    assert cropped.crs == crs_utm
    assert cropped.width == int(win.width)
    assert cropped.height == int(win.height)
    assert cropped.resolution == pytest.approx((pixel_size, pixel_size))
    # Bounds must remain inside original UTM extent and preserve valid -14.0 pixels
    assert cropped.bounds[0] >= bounds[0] and cropped.bounds[2] <= bounds[2]
    assert cropped.bounds[1] >= bounds[1] and cropped.bounds[3] <= bounds[3]
    assert np.allclose(cropped.array[~np.isnan(cropped.array)], -14.0)


def test_invalid_aoi_geometry_or_missing_crs_raises_explicitly():
    crs_utm = CRS.from_epsg(32643)
    transform = from_origin(373000.0, 2052000.0, 100.0, 100.0)
    bounds = (373000.0, 2046000.0, 379000.0, 2052000.0)
    arr = np.full((60, 60), -14.0, dtype=np.float32)

    # Bow-tie (self-intersecting invalid polygon)
    invalid_aoi = {
        "type": "Polygon",
        "coordinates": [[[73.8, 18.5], [73.9, 18.6], [73.9, 18.5], [73.8, 18.6], [73.8, 18.5]]],
    }
    with pytest.raises(AoiTransformError):
        compute_aoi_window(invalid_aoi, bounds, transform, 60, 60, raster_crs=crs_utm)

    # Missing raster CRS must raise explicitly rather than silently assuming EPSG:4326
    valid_aoi = {
        "type": "Polygon",
        "coordinates": [[[73.8, 18.5], [73.82, 18.5], [73.82, 18.52], [73.8, 18.52], [73.8, 18.5]]],
    }
    with pytest.raises(AoiTransformError):
        compute_aoi_window(valid_aoi, bounds, transform, 60, 60, raster_crs=None)

    # Validation must fail cleanly if raster CRS is missing
    raster_no_crs = RasterData(arr, transform, None, -9999.0, bounds, (100.0, 100.0), "dB")
    obs_a = Observation(
        id="obs_a",
        provider="local",
        synthetic=False,
        acquisition_date="2026-01-01T00:00:00Z",
        geometry=valid_aoi,
        asset_location="a.tif",
        asset_format="GTiff",
        measurement_units="dB",
        resolution=100.0,
        crs="EPSG:32643",
    )
    obs_b = obs_a.model_copy(update={"id": "obs_b", "acquisition_date": "2026-01-10T00:00:00Z"})
    res = validate_compatibility(
        obs_a,
        obs_b,
        valid_aoi,
        before_raster=raster_no_crs,
        after_raster=raster_no_crs,
    )
    assert res.compatible is False
    v_aoi = next(r for r in res.rules if r.id == "V-AOI")
    v_valid = next(r for r in res.rules if r.id == "V-VALID")
    assert v_aoi.passed is False
    assert v_valid.passed is False

