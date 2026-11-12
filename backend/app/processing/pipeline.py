import os
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from app.processing.readers.geotiff import GeoTIFFReader
from app.processing.metadata import find_sidecar, load_sidecar_metadata
from app.processing.preprocessing import crop_to_aoi
from app.processing.alignment import align
from app.processing.change_detection import difference_db
from app.processing.statistics import compute_stats
from app.processing.export import export_results

def run_pipeline(
    before_path: Path,
    after_path: Path,
    aoi_geojson: Optional[Dict[str, Any]],
    output_dir: Path,
    stage_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Orchestrate the raster processing pipeline through deterministic stages:
    reading -> aligning -> differencing -> statistics -> exporting -> completed.

    Calls stage_callback(stage) at each transition.
    Performs atomic cleanup of output_dir if an exception is raised.

    Args:
        before_path: Path to earlier observation GeoTIFF.
        after_path: Path to later observation GeoTIFF.
        aoi_geojson: Optional GeoJSON polygon geometry dictionary for spatial cropping.
        output_dir: Destination directory for exported products.
        stage_callback: Optional callable accepting the current stage name.

    Returns:
        Dict with exported file paths, statistics, bounds, metadata, and limitations.
    """
    output_dir = Path(output_dir)
    dir_existed_before = output_dir.exists()

    def notify(stage: str):
        if stage_callback is not None:
            stage_callback(stage)

    try:
        # Stage 1: reading
        notify("reading")
        reader = GeoTIFFReader()
        before_raster = reader.read(before_path)
        after_raster = reader.read(after_path)

        # Parse sidecar metadata if present
        before_sidecar = find_sidecar(before_path)
        after_sidecar = find_sidecar(after_path)
        before_meta = load_sidecar_metadata(before_sidecar) if before_sidecar else {"id": before_path.stem}
        after_meta = load_sidecar_metadata(after_sidecar) if after_sidecar else {"id": after_path.stem}

        is_synthetic = bool(before_meta.get("synthetic", False) or after_meta.get("synthetic", False))

        # Crop to AOI if provided
        if aoi_geojson and bool(aoi_geojson.get("coordinates")):
            before_raster = crop_to_aoi(before_raster, aoi_geojson)
            after_raster = crop_to_aoi(after_raster, aoi_geojson)

        # Stage 2: aligning
        notify("aligning")
        before_raster, after_raster = align(before_raster, after_raster)

        # Stage 3: differencing
        notify("differencing")
        diff_array = difference_db(before_raster, after_raster)

        # Stage 4: statistics
        notify("statistics")
        stats = compute_stats(diff_array, nodata=before_raster.nodata)

        # Stage 5: exporting
        notify("exporting")
        output_dir.mkdir(parents=True, exist_ok=True)

        combined_metadata = {
            "before_id": before_meta.get("id", before_path.stem),
            "after_id": after_meta.get("id", after_path.stem),
            "synthetic": is_synthetic,
            "before_observation": before_meta,
            "after_observation": after_meta,
        }

        export_res = export_results(
            diff_array=diff_array,
            transform=before_raster.transform,
            crs=before_raster.crs,
            stats=stats,
            metadata=combined_metadata,
            output_dir=output_dir,
            before_array=before_raster.array,
            after_array=after_raster.array,
            nodata=before_raster.nodata,
        )

        # Stage 6: completed
        notify("completed")
        return export_res

    except Exception:
        # Atomic cleanup on failure: remove generated output files
        if output_dir.exists():
            if not dir_existed_before:
                shutil.rmtree(output_dir, ignore_errors=True)
            else:
                for f in ["difference.tif", "statistics.json", "metadata.json", "difference.png", "before.png", "after.png"]:
                    p = output_dir / f
                    if p.exists():
                        try:
                            p.unlink()
                        except OSError:
                            pass
        notify("failed")
        raise
