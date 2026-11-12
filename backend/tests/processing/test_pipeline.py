import json
from pathlib import Path
import pytest
from app.processing.pipeline import run_pipeline

def test_full_pipeline_run_success(tmp_path):
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    before_path = fixtures_dir / "syn_before.tif"
    after_path = fixtures_dir / "syn_after.tif"

    with open(fixtures_dir / "aoi.geojson", "r") as f:
        aoi = json.load(f)

    output_dir = tmp_path / "job_success"
    recorded_stages = []

    def callback(stage: str):
        recorded_stages.append(stage)

    res = run_pipeline(
        before_path=before_path,
        after_path=after_path,
        aoi_geojson=aoi,
        output_dir=output_dir,
        stage_callback=callback,
    )

    # All stages should be invoked in order
    assert recorded_stages == [
        "reading",
        "aligning",
        "differencing",
        "statistics",
        "exporting",
        "completed",
    ]

    # Verify output contents
    assert (output_dir / "difference.tif").is_file()
    assert (output_dir / "statistics.json").is_file()
    assert (output_dir / "metadata.json").is_file()
    assert (output_dir / "difference.png").is_file()
    assert (output_dir / "before.png").is_file()
    assert (output_dir / "after.png").is_file()

    # Verify statistics match expected
    stats = res["statistics"]
    assert stats["valid_pixel_count"] == 4064
    assert stats["invalid_pixel_count"] == 32
    assert stats["total_pixel_count"] == 4096
    assert stats["mean"] == pytest.approx(-0.688976, rel=1e-4)
    assert res["synthetic"] is True
