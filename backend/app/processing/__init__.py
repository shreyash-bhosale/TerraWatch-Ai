from app.processing.alignment import AlignmentMismatchError, align, check_alignment
from app.processing.change_detection import difference_db
from app.processing.export import export_results
from app.processing.metadata import find_sidecar, load_sidecar_metadata, normalize_metadata
from app.processing.pipeline import run_pipeline
from app.processing.preprocessing import (
    AoiTransformError,
    EmptyWindowError,
    NoValidPixelsError,
    compute_aoi_window,
    crop_to_aoi,
    finalize_valid_raster,
    get_valid_mask,
    mask_nodata_to_nan,
    reproject_aoi_geometry,
)
from app.processing.raster_data import RasterData
from app.processing.readers.base import BaseReader
from app.processing.readers.geotiff import CorruptRasterError, GeoTIFFReader
from app.processing.statistics import compute_stats

__all__ = [
    "AlignmentMismatchError",
    "AoiTransformError",
    "BaseReader",
    "CorruptRasterError",
    "EmptyWindowError",
    "GeoTIFFReader",
    "NoValidPixelsError",
    "RasterData",
    "align",
    "check_alignment",
    "compute_aoi_window",
    "compute_stats",
    "crop_to_aoi",
    "difference_db",
    "export_results",
    "finalize_valid_raster",
    "find_sidecar",
    "get_valid_mask",
    "load_sidecar_metadata",
    "mask_nodata_to_nan",
    "normalize_metadata",
    "reproject_aoi_geometry",
    "run_pipeline",
]
