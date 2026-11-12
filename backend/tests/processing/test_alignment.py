from pathlib import Path
import numpy as np
import pytest
from rasterio.crs import CRS
from rasterio.transform import from_origin
from app.processing.readers.geotiff import GeoTIFFReader
from app.processing.alignment import check_alignment, align, AlignmentMismatchError
from app.processing.raster_data import RasterData

def test_identical_aligned_rasters_pass():
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    reader = GeoTIFFReader()
    before = reader.read(fixtures_dir / "syn_before.tif")
    after = reader.read(fixtures_dir / "syn_after.tif")

    assert check_alignment(before, after) is True
    aligned_before, aligned_after = align(before, after)
    assert aligned_before.shape == (64, 64)
    assert aligned_after.shape == (64, 64)
    assert aligned_before.transform == after.transform

def test_misaligned_resolution_raises_error():
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    reader = GeoTIFFReader()
    before = reader.read(fixtures_dir / "syn_before.tif")
    misaligned = reader.read(fixtures_dir / "syn_misaligned.tif")

    with pytest.raises(AlignmentMismatchError, match="Resolution mismatch"):
        check_alignment(before, misaligned)

    with pytest.raises(AlignmentMismatchError, match="Resolution mismatch"):
        align(before, misaligned)

def test_mismatched_crs_raises_error():
    transform = from_origin(73.8, 18.5, 0.001, 0.001)
    arr = np.zeros((10, 10), dtype=np.float32)
    r1 = RasterData(
        array=arr,
        transform=transform,
        crs=CRS.from_epsg(4326),
        nodata=-9999.0,
        bounds=(73.8, 18.49, 73.81, 18.5),
        resolution=(0.001, 0.001),
    )
    r2 = RasterData(
        array=arr,
        transform=transform,
        crs=CRS.from_epsg(3857),
        nodata=-9999.0,
        bounds=(73.8, 18.49, 73.81, 18.5),
        resolution=(0.001, 0.001),
    )

    with pytest.raises(AlignmentMismatchError, match="CRS mismatch"):
        check_alignment(r1, r2)

def test_disjoint_rasters_raise_error():
    t1 = from_origin(73.8, 18.5, 0.001, 0.001)
    t2 = from_origin(80.0, 25.0, 0.001, 0.001)
    arr = np.zeros((10, 10), dtype=np.float32)
    r1 = RasterData(
        array=arr,
        transform=t1,
        crs=CRS.from_epsg(4326),
        nodata=-9999.0,
        bounds=(73.8, 18.49, 73.81, 18.5),
        resolution=(0.001, 0.001),
    )
    r2 = RasterData(
        array=arr,
        transform=t2,
        crs=CRS.from_epsg(4326),
        nodata=-9999.0,
        bounds=(80.0, 24.99, 80.01, 25.0),
        resolution=(0.001, 0.001),
    )

    with pytest.raises(AlignmentMismatchError, match="do not overlap"):
        check_alignment(r1, r2)

def test_shifted_extent_crops_to_intersection():
    # Both rasters have pixel_size = 0.001, but r2 is shifted by 2 pixels right and down
    t1 = from_origin(73.800, 18.560, 0.001, 0.001)
    t2 = from_origin(73.802, 18.558, 0.001, 0.001)
    arr1 = np.ones((20, 20), dtype=np.float32) * 10.0
    arr2 = np.ones((20, 20), dtype=np.float32) * 20.0

    r1 = RasterData(
        array=arr1,
        transform=t1,
        crs=CRS.from_epsg(4326),
        nodata=-9999.0,
        bounds=(73.800, 18.540, 73.820, 18.560),
        resolution=(0.001, 0.001),
    )
    r2 = RasterData(
        array=arr2,
        transform=t2,
        crs=CRS.from_epsg(4326),
        nodata=-9999.0,
        bounds=(73.802, 18.538, 73.822, 18.558),
        resolution=(0.001, 0.001),
    )

    # They don't match exactly, but can align
    assert check_alignment(r1, r2) is False

    aligned1, aligned2 = align(r1, r2)
    assert aligned1.shape == aligned2.shape
    assert aligned1.shape == (18, 18)
    assert aligned1.transform == aligned2.transform
    assert aligned1.bounds == pytest.approx(aligned2.bounds)
