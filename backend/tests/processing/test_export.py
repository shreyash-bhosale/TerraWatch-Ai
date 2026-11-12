import json
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

from app.processing.change_detection import difference_db
from app.processing.export import export_results
from app.processing.readers.geotiff import GeoTIFFReader
from app.processing.statistics import compute_stats


def test_export_results_and_geotiff_roundtrip(tmp_path):
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    reader = GeoTIFFReader()
    before = reader.read(fixtures_dir / "syn_before.tif")
    after = reader.read(fixtures_dir / "syn_after.tif")

    diff = difference_db(before, after)
    stats = compute_stats(diff, nodata=before.nodata)

    metadata = {
        "synthetic": True,
        "product_name": "TEST_SYNTHETIC",
    }

    res = export_results(
        diff_array=diff,
        transform=before.transform,
        crs=before.crs,
        stats=stats,
        metadata=metadata,
        output_dir=tmp_path,
        before_array=before.array,
        after_array=after.array,
        nodata=-9999.0,
    )

    # Check exported files exist
    diff_tif = tmp_path / "difference.tif"
    stats_json = tmp_path / "statistics.json"
    meta_json = tmp_path / "metadata.json"
    diff_png = tmp_path / "difference.png"
    before_png = tmp_path / "before.png"
    after_png = tmp_path / "after.png"

    assert diff_tif.is_file()
    assert stats_json.is_file()
    assert meta_json.is_file()
    assert diff_png.is_file()
    assert before_png.is_file()
    assert after_png.is_file()

    # Verify GeoTIFF re-read matches original diff array
    with rasterio.open(diff_tif) as src:
        assert src.shape == (64, 64)
        assert src.crs == before.crs
        assert src.nodata == -9999.0
        reread_arr = src.read(1)

        # Check valid pixels match
        valid_mask = ~np.isnan(diff)
        assert np.allclose(reread_arr[valid_mask], diff[valid_mask])
        # Check nodata pixels are -9999.0
        assert np.all(reread_arr[~valid_mask] == -9999.0)

    # Check bounds
    assert len(res["bounds"]) == 4
    west, south, east, north = res["bounds"]
    assert west < east
    assert south < north

    # Check metadata and limitations
    with open(meta_json, "r") as f:
        meta_content = json.load(f)
    assert meta_content["synthetic"] is True
    assert any("DEMO DATA" in lim for lim in meta_content["limitations"])
    assert "color_scales" in meta_content
    assert meta_content["color_scales"]["difference"]["symmetric"] is True
    assert meta_content["color_scales"]["difference"]["colormap"] == "coolwarm"
    assert meta_content["color_scales"]["before"]["colormap"] == "gray"
    assert meta_content["color_scales"]["after"]["colormap"] == "gray"

    # Check difference PNG image properties
    img = Image.open(diff_png)
    assert img.mode == "RGBA"
    assert img.size == (64, 64)
    img_arr = np.array(img)
    # Check that invalid pixels (e.g. [0, 0]) have alpha == 0
    assert img_arr[0, 0, 3] == 0
    # Check that valid pixels (e.g. [10, 10]) have alpha == 255
    assert img_arr[10, 10, 3] == 255

    # Check before/after PNGs use consistent single-hue grayscale ramp and preserve nodata alpha
    b_img = Image.open(before_png)
    a_img = Image.open(after_png)
    assert b_img.mode == "RGBA" and b_img.size == (64, 64)
    assert a_img.mode == "RGBA" and a_img.size == (64, 64)
    b_arr = np.array(b_img)
    a_arr = np.array(a_img)
    # Valid pixel channels R == G == B (grayscale)
    assert b_arr[10, 10, 0] == b_arr[10, 10, 1] == b_arr[10, 10, 2]
    assert a_arr[10, 10, 0] == a_arr[10, 10, 1] == a_arr[10, 10, 2]
    assert b_arr[10, 10, 3] == 255
    assert a_arr[10, 10, 3] == 255
    # Nodata blocks transparent: syn_before rows 0..3, cols 0..3; syn_after rows 60..63, cols 60..63
    assert b_arr[0, 0, 3] == 0
    assert a_arr[63, 63, 3] == 0
