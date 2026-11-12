import numpy as np
from app.processing.raster_data import RasterData

def difference_db(before: RasterData, after: RasterData) -> np.ndarray:
    """
    Compute calibrated SAR backscatter change D = B2 - B1 in decibels (dB).

    Only computes difference where both before and after pixels are finite,
    non-NaN, and not equal to their respective nodata values.
    All other pixels are set to np.nan in memory.

    Args:
        before: Earlier observation RasterData (B1).
        after: Later observation RasterData (B2).

    Returns:
        2D float32 numpy array containing difference values in dB, with np.nan for invalid pixels.
    """
    if before.shape != after.shape:
        raise ValueError(
            f"Shape mismatch in change detection: before={before.shape}, after={after.shape}. "
            "Rasters must be aligned prior to differencing."
        )

    # Valid mask for both rasters
    valid_before = (
        np.isfinite(before.array) &
        (~np.isnan(before.array)) &
        (~np.isclose(before.array, before.nodata))
    )
    valid_after = (
        np.isfinite(after.array) &
        (~np.isnan(after.array)) &
        (~np.isclose(after.array, after.nodata))
    )

    valid_mask = valid_before & valid_after

    diff = np.full(before.shape, np.nan, dtype=np.float32)
    diff[valid_mask] = after.array[valid_mask] - before.array[valid_mask]

    return diff
