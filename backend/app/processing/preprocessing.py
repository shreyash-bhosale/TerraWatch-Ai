from typing import Any, Dict, Tuple
import numpy as np
import rasterio
from rasterio.windows import Window
from shapely.geometry import shape

from app.processing.raster_data import RasterData

class EmptyWindowError(ValueError):
    """Raised when the AOI does not intersect the raster or has empty intersection."""
    pass

class NoValidPixelsError(ValueError):
    """Raised when an extracted raster window contains no valid pixels."""
    pass

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

def compute_aoi_window(
    aoi_geometry: Dict[str, Any],
    raster_bounds: Tuple[float, float, float, float],
    transform: rasterio.Affine,
    width: int,
    height: int,
) -> Window:
    """
    Compute pixel window corresponding to an AOI GeoJSON geometry intersected with raster bounds.
    """
    geom = shape(aoi_geometry)
    if geom.is_empty:
        raise EmptyWindowError("Provided AOI geometry is empty")

    minx, miny, maxx, maxy = geom.bounds
    r_w, r_s, r_e, r_n = raster_bounds

    # Check for disjoint bounds
    if minx >= r_e or maxx <= r_w or miny >= r_n or maxy <= r_s:
        raise EmptyWindowError(
            f"AOI bounds [{minx}, {miny}, {maxx}, {maxy}] do not intersect "
            f"raster bounds [{r_w}, {r_s}, r_e={r_e}, r_n={r_n}]"
        )

    # Intersect geographic bounding boxes
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

def crop_to_aoi(raster: RasterData, aoi_geometry: Dict[str, Any]) -> RasterData:
    """
    Crop RasterData to an AOI GeoJSON geometry and mask nodata to NaN.
    Rejects with EmptyWindowError if window is empty, or NoValidPixelsError if no valid pixels remain.
    """
    window = compute_aoi_window(
        aoi_geometry=aoi_geometry,
        raster_bounds=raster.bounds,
        transform=raster.transform,
        width=raster.width,
        height=raster.height,
    )

    r_start = int(window.row_off)
    r_end = int(window.row_off + window.height)
    c_start = int(window.col_off)
    c_end = int(window.col_off + window.width)

    cropped_arr = raster.array[r_start:r_end, c_start:c_end]
    new_transform = rasterio.windows.transform(window, raster.transform)
    w, s, e, n = rasterio.windows.bounds(window, raster.transform)
    new_bounds = (float(w), float(s), float(e), float(n))

    # Mask nodata to NaN
    masked_arr = mask_nodata_to_nan(cropped_arr, nodata=raster.nodata)

    # Check valid pixels
    valid_count = np.count_nonzero(get_valid_mask(masked_arr, nodata=raster.nodata))
    if valid_count == 0:
        raise NoValidPixelsError("No valid pixels remain within the extracted AOI window")

    return RasterData(
        array=masked_arr,
        transform=new_transform,
        crs=raster.crs,
        nodata=raster.nodata,
        bounds=new_bounds,
        resolution=raster.resolution,
        units=raster.units,
    )
