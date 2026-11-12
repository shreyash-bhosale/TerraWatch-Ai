from pathlib import Path
import numpy as np
import pytest
from rasterio.crs import CRS
from rasterio.transform import from_origin
from app.processing.readers.geotiff import GeoTIFFReader
from app.processing.change_detection import difference_db
from app.processing.raster_data import RasterData

def test_difference_db_on_synthetic_fixtures():
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    reader = GeoTIFFReader()
    before = reader.read(fixtures_dir / "syn_before.tif")
    after = reader.read(fixtures_dir / "syn_after.tif")

    diff = difference_db(before, after)
    assert diff.shape == (64, 64)

    # Top-left 4x4 was nodata in before -> must be NaN
    assert np.all(np.isnan(diff[0:4, 0:4]))
    # Bottom-right 4x4 was nodata in after -> must be NaN
    assert np.all(np.isnan(diff[60:64, 60:64]))

    # Changed block rows 20-39, cols 20-39: (-22.0) - (-15.0) = -7.0 dB
    assert np.all(diff[20:40, 20:40] == pytest.approx(-7.0))

    # Remaining valid pixels: (-15.0) - (-15.0) = 0.0 dB
    # Valid mask
    valid_mask = ~np.isnan(diff)
    assert np.count_nonzero(valid_mask) == 4064
    assert np.count_nonzero(~valid_mask) == 32

    # Check that changed pixels count is exactly 400
    changed_mask = valid_mask & (diff == -7.0)
    assert np.count_nonzero(changed_mask) == 400

    unchanged_mask = valid_mask & (diff == 0.0)
    assert np.count_nonzero(unchanged_mask) == 3664

def test_difference_shape_mismatch_raises():
    t = from_origin(0, 0, 1, 1)
    crs = CRS.from_epsg(4326)
    r1 = RasterData(array=np.zeros((10, 10), dtype=np.float32), transform=t, crs=crs, nodata=-9999.0, bounds=(0, -10, 10, 0), resolution=(1, 1))
    r2 = RasterData(array=np.zeros((12, 12), dtype=np.float32), transform=t, crs=crs, nodata=-9999.0, bounds=(0, -12, 12, 0), resolution=(1, 1))

    with pytest.raises(ValueError, match="Shape mismatch"):
        difference_db(r1, r2)
