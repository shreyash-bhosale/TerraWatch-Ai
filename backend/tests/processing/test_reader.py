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


def test_read_metadata_avoids_pixel_load(monkeypatch):
    import rasterio.io
    from app.processing.pipeline import run_pipeline

    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    before_path = fixtures_dir / "syn_before.tif"
    reader = GeoTIFFReader()

    def _forbid_pixel_read(*args, **kwargs):
        raise AssertionError("read_metadata must not call DatasetReader.read")

    monkeypatch.setattr(rasterio.io.DatasetReader, "read", _forbid_pixel_read)
    meta = reader.read_metadata(before_path)
    assert meta["width"] == 64
    assert meta["height"] == 64
    assert meta["crs"].to_string() == "EPSG:4326"
    assert meta["nodata"] == -9999.0
    assert meta["resolution"] == pytest.approx((0.001, 0.001))


def test_pipeline_uses_windowed_read_for_aoi(tmp_path, monkeypatch):
    from app.processing.pipeline import run_pipeline

    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    recorded_windows = []
    orig_read = GeoTIFFReader.read

    def spy_read(self, path, window=None):
        recorded_windows.append((Path(path).name, window))
        return orig_read(self, path, window=window)

    monkeypatch.setattr(GeoTIFFReader, "read", spy_read)

    # Subset 20x20 window covering changed block in syn_after (rows 20-39, cols 20-39)
    subset_aoi = {
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

    res = run_pipeline(
        before_path=fixtures_dir / "syn_before.tif",
        after_path=fixtures_dir / "syn_after.tif",
        aoi_geojson=subset_aoi,
        output_dir=tmp_path / "out",
    )

    assert len(recorded_windows) == 2
    for fname, win in recorded_windows:
        assert fname in ("syn_before.tif", "syn_after.tif")
        assert win is not None
        assert win == Window(col_off=20, row_off=20, width=20, height=20)
        assert win.width < 64 and win.height < 64

    assert res["statistics"]["total_pixel_count"] == 400
    assert res["statistics"]["valid_pixel_count"] == 400
    assert res["statistics"]["mean"] == pytest.approx(-7.0, abs=1e-6)

