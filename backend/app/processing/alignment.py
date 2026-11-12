
import numpy as np
import rasterio
from rasterio.windows import Window

from app.processing.raster_data import RasterData


class AlignmentMismatchError(Exception):
    """Raised when two rasters have incompatible CRS, resolution, or non-overlapping grids."""

def check_alignment(a: RasterData, b: RasterData) -> bool:
    """
    Check spatial compatibility between two RasterData objects.

    Returns:
        True: if CRS, resolution, transform, bounds, and shape are identical.
        False: if grids have identical CRS and resolution with shifted overlapping extent (alignable).

    Raises:
        AlignmentMismatchError: if grids have mismatched CRS, mismatched resolution,
        no spatial overlap, or sub-pixel phase shifts that cannot be aligned without resampling.
    """
    # 1. Check CRS
    if a.crs != b.crs:
        raise AlignmentMismatchError(f"CRS mismatch: {a.crs} != {b.crs}")

    # 2. Check Resolution
    res_match = (
        np.isclose(a.resolution[0], b.resolution[0], rtol=1e-4) and
        np.isclose(a.resolution[1], b.resolution[1], rtol=1e-4)
    )
    if not res_match:
        raise AlignmentMismatchError(
            f"Resolution mismatch: {a.resolution} != {b.resolution}"
        )

    # 3. Check exact match of transform, bounds, and shape
    shape_match = a.shape == b.shape
    bounds_match = all(np.isclose(a.bounds[i], b.bounds[i], atol=1e-5) for i in range(4))
    transform_match = all(
        np.isclose(a.transform[i], b.transform[i], atol=1e-5) for i in range(6)
    )

    if shape_match and bounds_match and transform_match:
        return True

    # 4. Check whether shifted extents overlap
    int_w = max(a.bounds[0], b.bounds[0])
    int_s = max(a.bounds[1], b.bounds[1])
    int_e = min(a.bounds[2], b.bounds[2])
    int_n = min(a.bounds[3], b.bounds[3])

    if (int_w >= int_e) or (int_s >= int_n):
        raise AlignmentMismatchError(
            f"Raster extents do not overlap: bounds A={a.bounds}, bounds B={b.bounds}"
        )

    # 5. Check integer pixel grid alignment (no sub-pixel phase shift)
    rx, ry = a.resolution
    dx = (b.transform.c - a.transform.c) / rx
    dy = (b.transform.f - a.transform.f) / ry

    if abs(dx - round(dx)) > 1e-3 or abs(dy - round(dy)) > 1e-3:
        raise AlignmentMismatchError(
            f"Sub-pixel grid shift detected (dx={dx:.4f}, dy={dy:.4f}). "
            "Resampling is not supported; only integer-shifted extents can be aligned."
        )

    return False

def align(a: RasterData, b: RasterData) -> tuple[RasterData, RasterData]:
    """
    Ensure both rasters occupy identical spatial grids.
    If already matching, returns (a, b) unchanged.
    If same CRS and resolution with shifted extent, crops both to their intersection.
    Raises AlignmentMismatchError for any incompatible mismatch.
    """
    is_matching = check_alignment(a, b)
    if is_matching:
        return a, b

    # Rasters are compatible but have shifted extents: crop to intersection
    int_w = max(a.bounds[0], b.bounds[0])
    int_s = max(a.bounds[1], b.bounds[1])
    int_e = min(a.bounds[2], b.bounds[2])
    int_n = min(a.bounds[3], b.bounds[3])

    win_a = rasterio.windows.from_bounds(
        int_w, int_s, int_e, int_n, transform=a.transform
    ).round_offsets().round_lengths()
    win_b = rasterio.windows.from_bounds(
        int_w, int_s, int_e, int_n, transform=b.transform
    ).round_offsets().round_lengths()

    c_start_a, c_end_a = int(win_a.col_off), int(win_a.col_off + win_a.width)
    r_start_a, r_end_a = int(win_a.row_off), int(win_a.row_off + win_a.height)

    c_start_b, c_end_b = int(win_b.col_off), int(win_b.col_off + win_b.width)
    r_start_b, r_end_b = int(win_b.row_off), int(win_b.row_off + win_b.height)

    arr_a = a.array[r_start_a:r_end_a, c_start_a:c_end_a]
    arr_b = b.array[r_start_b:r_end_b, c_start_b:c_end_b]

    # Ensure exact dimensions
    target_h = min(arr_a.shape[0], arr_b.shape[0])
    target_w = min(arr_a.shape[1], arr_b.shape[1])

    if target_h <= 0 or target_w <= 0:
        raise AlignmentMismatchError("Overlap between rasters is empty")

    arr_a = arr_a[:target_h, :target_w]
    arr_b = arr_b[:target_h, :target_w]

    final_win = Window(c_start_a, r_start_a, target_w, target_h)
    new_transform = rasterio.windows.transform(final_win, a.transform)
    w, s, e, n = rasterio.windows.bounds(final_win, a.transform)
    new_bounds = (float(w), float(s), float(e), float(n))

    aligned_a = RasterData(
        array=arr_a,
        transform=new_transform,
        crs=a.crs,
        nodata=a.nodata,
        bounds=new_bounds,
        resolution=a.resolution,
        units=a.units,
    )
    aligned_b = RasterData(
        array=arr_b,
        transform=new_transform,
        crs=b.crs,
        nodata=b.nodata,
        bounds=new_bounds,
        resolution=b.resolution,
        units=b.units,
    )

    return aligned_a, aligned_b
