from typing import Any

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.warp import transform_geom
from rasterio.windows import Window
from shapely.geometry import shape

from app.processing.raster_data import RasterData


class EmptyWindowError(ValueError):
    """Raised when the AOI does not intersect the raster or has empty intersection."""


class NoValidPixelsError(ValueError):
    """Raised when an extracted raster window contains no valid pixels."""


class AoiTransformError(ValueError):
    """Raised when an AOI geometry is invalid or cannot be transformed to the raster CRS."""


def mask_nodata_to_nan(array: np.ndarray, nodata: float = -9999.0) -> np.ndarray:
    """
    Return a float32 array where nodata and non-finite values are replaced with np.nan.
    Never alters values in-place; returns a copy.
    """
    arr = array.copy().astype(np.float32)
    invalid_mask = np.isclose(arr, nodata) | np.isnan(arr) | (~np.isfinite(arr))
    arr[invalid_mask] = np.nan
    return arr


def get_valid_mask(array: np.ndarray, nodata: float = -9999.0) -> np.ndarray:
    """
    Return a boolean mask where True indicates a valid, finite observation pixel.
    """
    return np.isfinite(array) & (~np.isnan(array)) & (~np.isclose(array, nodata))


def reproject_aoi_geometry(
    aoi_geometry: dict[str, Any],
    raster_crs: Any,
    aoi_crs: str = "EPSG:4326",
) -> dict[str, Any]:
    """
    Validate an AOI GeoJSON geometry and transform it into the target raster CRS.
    """
    if raster_crs is None:
        raise AoiTransformError("Raster CRS is missing; cannot transform AOI geometry")

    try:
        src_geom = shape(aoi_geometry)
    except Exception as e:
        raise AoiTransformError(f"Invalid AOI geometry: {e}") from e

    if src_geom.is_empty:
        raise EmptyWindowError("Provided AOI geometry is empty")
    if not src_geom.is_valid:
        raise AoiTransformError("Provided AOI geometry is topologically invalid")

    try:
        target_crs = CRS.from_user_input(raster_crs)
        source_crs = CRS.from_user_input(aoi_crs)
    except Exception as e:
        raise AoiTransformError(f"Invalid CRS specification for AOI transformation: {e}") from e

    if target_crs == source_crs:
        return aoi_geometry

    try:
        transformed = transform_geom(source_crs, target_crs, aoi_geometry)
        dst_geom = shape(transformed)
    except Exception as e:
        raise AoiTransformError(
            f"Failed to transform AOI from {source_crs} to {target_crs}: {e}"
        ) from e

    if dst_geom.is_empty or not np.all(np.isfinite(dst_geom.bounds)):
        raise AoiTransformError("Transformed AOI geometry is empty or has non-finite bounds")

    return transformed


def compute_aoi_window(
    aoi_geometry: dict[str, Any],
    raster_bounds: tuple[float, float, float, float],
    transform: rasterio.Affine,
    width: int,
    height: int,
    raster_crs: Any,
    aoi_crs: str = "EPSG:4326",
) -> Window:
    """
    Compute pixel window corresponding to an AOI GeoJSON geometry intersected with raster bounds
    after transforming the AOI into the raster's native CRS.
    """
    transformed_aoi = reproject_aoi_geometry(
        aoi_geometry=aoi_geometry,
        raster_crs=raster_crs,
        aoi_crs=aoi_crs,
    )
    geom = shape(transformed_aoi)
    minx, miny, maxx, maxy = geom.bounds
    r_w, r_s, r_e, r_n = raster_bounds

    # Check for disjoint bounds in raster CRS
    if minx >= r_e or maxx <= r_w or miny >= r_n or maxy <= r_s:
        raise EmptyWindowError(
            f"AOI bounds [{minx}, {miny}, {maxx}, {maxy}] do not intersect "
            f"raster bounds [{r_w}, {r_s}, r_e={r_e}, r_n={r_n}]"
        )

    # Intersect bounding boxes in raster CRS
    clip_minx = max(minx, r_w)
    clip_maxx = min(maxx, r_e)
    clip_miny = max(miny, r_s)
    clip_maxy = min(maxy, r_n)

    raw_window = rasterio.windows.from_bounds(
        clip_minx, clip_miny, clip_maxx, clip_maxy, transform=transform
    ).round_offsets().round_lengths()

    col_start = max(0, min(width, int(raw_window.col_off)))
    col_end = max(0, min(width, int(raw_window.col_off + raw_window.width)))
    row_start = max(0, min(height, int(raw_window.row_off)))
    row_end = max(0, min(height, int(raw_window.row_off + raw_window.height)))

    win_w = col_end - col_start
    win_h = row_end - row_start

    if win_w <= 0 or win_h <= 0:
        raise EmptyWindowError("Intersection of AOI and raster extent results in an empty window")

    return Window(col_start, row_start, win_w, win_h)


def finalize_valid_raster(raster: RasterData) -> RasterData:
    """
    Mask nodata values to NaN and reject windows with zero valid pixels.
    Shared by full-raster cropping and windowed-read pipeline steps.
    """
    masked_arr = mask_nodata_to_nan(raster.array, nodata=raster.nodata)
    valid_count = np.count_nonzero(get_valid_mask(masked_arr, nodata=raster.nodata))
    if valid_count == 0:
        raise NoValidPixelsError("No valid pixels remain within the extracted AOI window")

    return RasterData(
        array=masked_arr,
        transform=raster.transform,
        crs=raster.crs,
        nodata=raster.nodata,
        bounds=raster.bounds,
        resolution=raster.resolution,
        units=raster.units,
    )


def crop_to_aoi(
    raster: RasterData,
    aoi_geometry: dict[str, Any],
    aoi_crs: str = "EPSG:4326",
) -> RasterData:
    """
    Crop RasterData to an AOI GeoJSON geometry and mask nodata to NaN.
    Rejects with EmptyWindowError if window is empty, AoiTransformError on CRS failure,
    or NoValidPixelsError if no valid pixels remain.
    """
    window = compute_aoi_window(
        aoi_geometry=aoi_geometry,
        raster_bounds=raster.bounds,
        transform=raster.transform,
        width=raster.width,
        height=raster.height,
        raster_crs=raster.crs,
        aoi_crs=aoi_crs,
    )

    r_start = int(window.row_off)
    r_end = int(window.row_off + window.height)
    c_start = int(window.col_off)
    c_end = int(window.col_off + window.width)

    cropped_arr = raster.array[r_start:r_end, c_start:c_end]
    new_transform = rasterio.windows.transform(window, raster.transform)
    w, s, e, n = rasterio.windows.bounds(window, raster.transform)
    new_bounds = (float(w), float(s), float(e), float(n))

    cropped_raster = RasterData(
        array=cropped_arr,
        transform=new_transform,
        crs=raster.crs,
        nodata=raster.nodata,
        bounds=new_bounds,
        resolution=raster.resolution,
        units=raster.units,
    )
    return finalize_valid_raster(cropped_raster)
