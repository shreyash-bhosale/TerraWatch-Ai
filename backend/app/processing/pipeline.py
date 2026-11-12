import logging
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rasterio.crs import CRS
from rasterio.errors import RasterioError
from rasterio.warp import transform_bounds

from app.processing.alignment import align
from app.processing.change_detection import difference_db
from app.processing.export import export_results
from app.processing.metadata import find_sidecar, load_sidecar_metadata
from app.processing.preprocessing import (
    compute_aoi_window,
    finalize_valid_raster,
)
from app.processing.readers.geotiff import GeoTIFFReader
from app.processing.statistics import compute_stats
from app.processing.validation import validate_compatibility
from app.schemas.observation import Observation

logger = logging.getLogger(__name__)


class IncompatiblePipelineError(ValueError):
    """Raised when observation pair fails compatibility validation inside pipeline."""

    def __init__(self, message: str):
        super().__init__(message)
        self.code = "INCOMPATIBLE_OBSERVATIONS"


def _bounds_to_wgs84_polygon(
    bounds: tuple[float, float, float, float],
    crs: Any = None,
) -> dict[str, Any]:
    w, s, e, n = bounds
    if crs is not None:
        try:
            if CRS.from_user_input(crs) != CRS.from_epsg(4326):
                w, s, e, n = transform_bounds(crs, "EPSG:4326", w, s, e, n)
        except (RasterioError, ValueError, TypeError) as exc:
            logger.warning("Failed to reproject raster bounds from %r to EPSG:4326: %s", crs, exc)
    return {
        "type": "Polygon",
        "coordinates": [[[float(w), float(s)], [float(e), float(s)], [float(e), float(n)], [float(w), float(n)], [float(w), float(s)]]],
    }


def _build_observation(
    meta: dict[str, Any] | None,
    header: dict[str, Any],
    path: Path,
    default_date: str,
) -> Observation:
    if meta and "id" in meta and "geometry" in meta and meta.get("acquisition_date"):
        return Observation.model_validate(meta)

    crs = header["crs"]
    return Observation(
        id=str((meta or {}).get("id") or path.stem),
        provider=str((meta or {}).get("provider") or "local"),
        synthetic=bool((meta or {}).get("synthetic", False)),
        acquisition_date=str((meta or {}).get("acquisition_date") or default_date),
        geometry=(meta or {}).get("geometry") or _bounds_to_wgs84_polygon(header["bounds"], crs),
        asset_location=str(path),
        asset_format="GTiff",
        measurement_units=(meta or {}).get("measurement_units") or header["units"],
        resolution=(meta or {}).get("resolution") or float(header["resolution"][0]),
        crs=(meta or {}).get("crs") or (str(crs) if crs else None),
    )


def run_pipeline(
    before_path: Path,
    after_path: Path,
    aoi_geojson: dict[str, Any] | None,
    output_dir: Path,
    stage_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """
    Orchestrate the raster processing pipeline through deterministic stages:
    reading -> aligning -> differencing -> statistics -> exporting -> completed.

    Uses header inspection + AOI window calculation before reading pixel data
    so only the AOI window is loaded from disk when an AOI is supplied.
    Performs atomic cleanup of output_dir if an exception is raised.
    """
    output_dir = Path(output_dir)
    dir_existed_before = output_dir.exists()

    def notify(stage: str):
        if stage_callback is not None:
            stage_callback(stage)

    try:
        # Stage 1: reading (inspect headers first; defer pixel reads to AOI window)
        notify("reading")
        reader = GeoTIFFReader()
        before_hdr = reader.read_metadata(before_path)
        after_hdr = reader.read_metadata(after_path)

        # Parse sidecar metadata if present
        before_sidecar = find_sidecar(before_path)
        after_sidecar = find_sidecar(after_path)
        before_meta = load_sidecar_metadata(before_sidecar) if before_sidecar else {"id": before_path.stem}
        after_meta = load_sidecar_metadata(after_sidecar) if after_sidecar else {"id": after_path.stem}

        is_synthetic = bool(before_meta.get("synthetic", False) or after_meta.get("synthetic", False))

        obs_before = _build_observation(
            before_sidecar and before_meta or None,
            before_hdr,
            before_path,
            "1970-01-01T00:00:00Z",
        )
        obs_after = _build_observation(
            after_sidecar and after_meta or None,
            after_hdr,
            after_path,
            "1970-01-02T00:00:00Z",
        )
        has_aoi = bool(aoi_geojson and aoi_geojson.get("coordinates"))
        aoi_for_validation = (
            aoi_geojson
            if has_aoi
            else _bounds_to_wgs84_polygon(before_hdr["bounds"], before_hdr["crs"])
        )

        # Run metadata and footprint compatibility checks before reading pixels
        pre_val = validate_compatibility(
            obs_a=obs_before,
            obs_b=obs_after,
            aoi_geometry=aoi_for_validation,
        )
        if not pre_val.compatible:
            failed_msgs = [r.message for r in pre_val.rules if not r.passed and r.severity == "error"]
            raise IncompatiblePipelineError(f"Incompatible observations: {'; '.join(failed_msgs)}")

        # Compute AOI windows from header metadata and perform windowed pixel reads
        if has_aoi:
            assert aoi_geojson is not None
            win_before = compute_aoi_window(
                aoi_geometry=aoi_geojson,
                raster_bounds=before_hdr["bounds"],
                transform=before_hdr["transform"],
                width=before_hdr["width"],
                height=before_hdr["height"],
                raster_crs=before_hdr["crs"],
            )
            win_after = compute_aoi_window(
                aoi_geometry=aoi_geojson,
                raster_bounds=after_hdr["bounds"],
                transform=after_hdr["transform"],
                width=after_hdr["width"],
                height=after_hdr["height"],
                raster_crs=after_hdr["crs"],
            )
            before_raster = reader.read(before_path, window=win_before)
            after_raster = reader.read(after_path, window=win_after)
        else:
            before_raster = reader.read(before_path)
            after_raster = reader.read(after_path)

        # Validate pixel-level compatibility (V-VALID) on the windowed rasters
        val_res = validate_compatibility(
            obs_a=obs_before,
            obs_b=obs_after,
            aoi_geometry=aoi_for_validation,
            before_raster=before_raster,
            after_raster=after_raster,
            rasters_pre_windowed=True,
        )
        if not val_res.compatible:
            failed_msgs = [r.message for r in val_res.rules if not r.passed and r.severity == "error"]
            raise IncompatiblePipelineError(f"Incompatible observations: {'; '.join(failed_msgs)}")

        # Mask nodata to NaN and reject empty-valid windows using shared helper
        before_raster = finalize_valid_raster(before_raster)
        after_raster = finalize_valid_raster(after_raster)

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
