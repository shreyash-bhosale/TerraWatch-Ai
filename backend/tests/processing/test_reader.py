from pathlib import Path
import numpy as np
import pytest
from rasterio.windows import Window
from app.processing.readers.geotiff import GeoTIFFReader

def test_geotiff_reader_reads_synthetic_before():
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    before_path = fixtures_dir / "syn_before.tif"

    reader = GeoTIFFReader()
    raster = reader.read(before_path)

    assert raster.shape == (64, 64)
    assert raster.width == 64
    assert raster.height == 64
    assert raster.crs.to_string() == "EPSG:4326"
    assert raster.nodata == -9999.0
    assert raster.resolution == pytest.approx((0.001, 0.001))
    assert raster.units == "dB"

    # Check that nodata block rows 0-3, cols 0-3 are -9999.0
    assert np.all(raster.array[0:4, 0:4] == -9999.0)
    # Remaining pixels are -15.0
    mask_valid = raster.array != -9999.0
    assert np.all(raster.array[mask_valid] == -15.0)

def test_geotiff_reader_window_crop():
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    after_path = fixtures_dir / "syn_after.tif"

    reader = GeoTIFFReader()
    # Read a 20x20 window centered on the changed region (rows 20-39, cols 20-39)
    window = Window(col_off=20, row_off=20, width=20, height=20)
    raster_window = reader.read(after_path, window=window)

    assert raster_window.shape == (20, 20)
    # All pixels in this window should be -22.0
    assert np.all(raster_window.array == -22.0)
    assert raster_window.resolution == pytest.approx((0.001, 0.001))

def test_reader_file_not_found():
    reader = GeoTIFFReader()
    with pytest.raises(FileNotFoundError):
        reader.read(Path("/nonexistent/path/to/raster.tif"))
