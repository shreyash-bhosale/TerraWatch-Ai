from pathlib import Path

import pytest

from app.processing.pipeline import run_pipeline
from app.processing.readers.geotiff import CorruptRasterError, GeoTIFFReader


def test_corrupt_raster_file_raises_cleanly(tmp_path):
    corrupt_file = tmp_path / "corrupt.tif"
    # Write garbage bytes that cannot be a valid TIFF
    corrupt_file.write_bytes(b"NOT_A_VALID_TIFF_HEADER_1234567890\x00\xff\xfe\xca\xfe")

    reader = GeoTIFFReader()
    with pytest.raises(CorruptRasterError):
        reader.read(corrupt_file)

def test_pipeline_atomic_cleanup_on_corrupt_raster(tmp_path):
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    before_path = fixtures_dir / "syn_before.tif"

    corrupt_after = tmp_path / "corrupt_after.tif"
    corrupt_after.write_bytes(b"INVALID_TIFF_BYTES")

    output_dir = tmp_path / "outputs" / "job_failed"

    stage_events = []
    def callback(stage: str):
        stage_events.append(stage)

    with pytest.raises(CorruptRasterError):
        run_pipeline(
            before_path=before_path,
            after_path=corrupt_after,
            aoi_geojson=None,
            output_dir=output_dir,
            stage_callback=callback,
        )

    # Output directory must not contain partial files or should have been cleaned up
    assert not output_dir.exists() or len(list(output_dir.iterdir())) == 0
    # Last stage recorded should be failed
    assert "failed" in stage_events
