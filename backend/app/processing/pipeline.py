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
from app.processing.raster_data import RasterData
from app.processing.validation import validate_compatibility
from app.schemas.observation import Observation


class IncompatiblePipelineError(ValueError):
    """Raised when observation pair fails compatibility validation inside pipeline."""

    def __init__(self, message: str):
        super().__init__(message)
        self.code = "INCOMPATIBLE_OBSERVATIONS"


def _bounds_to_polygon(bounds: tuple[float, float, float, float]) -> Dict[str, Any]:
    w, s, e, n = bounds
    return {
        "type": "Polygon",
        "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
    }


def _build_observation(
    meta: Optional[Dict[str, Any]],
    raster: RasterData,
    path: Path,
    default_date: str,
) -> Observation:
    if meta and "id" in meta and "geometry" in meta and meta.get("acquisition_date"):
        return Observation.model_validate(meta)

    return Observation(
        id=str((meta or {}).get("id") or path.stem),
        provider=str((meta or {}).get("provider") or "local"),
        synthetic=bool((meta or {}).get("synthetic", False)),
        acquisition_date=str((meta or {}).get("acquisition_date") or default_date),
        geometry=(meta or {}).get("geometry") or _bounds_to_polygon(raster.bounds),
        asset_location=str(path),
        asset_format="GTiff",
        measurement_units=(meta or {}).get("measurement_units") or raster.units,
        resolution=(meta or {}).get("resolution") or float(raster.resolution[0]),
        crs=(meta or {}).get("crs") or (str(raster.crs) if raster.crs else None),
    )


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

        # Validate compatibility via single source of truth before cropping/aligning
        obs_before = _build_observation(
            before_sidecar and before_meta or None,
            before_raster,
            before_path,
            "1970-01-01T00:00:00Z",
        )
        obs_after = _build_observation(
            after_sidecar and after_meta or None,
            after_raster,
            after_path,
            "1970-01-02T00:00:00Z",
        )
        aoi_for_validation = (
            aoi_geojson
            if (aoi_geojson and bool(aoi_geojson.get("coordinates")))
            else _bounds_to_polygon(before_raster.bounds)
        )
        val_res = validate_compatibility(
            obs_a=obs_before,
            obs_b=obs_after,
            aoi_geometry=aoi_for_validation,
            before_raster=before_raster,
            after_raster=after_raster,
        )
        if not val_res.compatible:
            failed_msgs = [r.message for r in val_res.rules if not r.passed and r.severity == "error"]
            raise IncompatiblePipelineError(f"Incompatible observations: {'; '.join(failed_msgs)}")

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
