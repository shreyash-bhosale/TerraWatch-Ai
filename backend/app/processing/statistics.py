from typing import Any, Dict
import numpy as np

def compute_stats(diff_array: np.ndarray, nodata: float = -9999.0) -> Dict[str, Any]:
    """
    Compute summary statistics on valid pixels of a difference array.

    Valid pixels are finite, non-NaN, and not equal to nodata.

    Args:
        diff_array: 2D numpy array of differences in dB.
        nodata: Nodata sentinel value (default -9999.0).

    Returns:
        Dictionary containing:
        - valid_pixel_count (int)
        - invalid_pixel_count (int)
        - total_pixel_count (int)
        - mean (float)
        - median (float)
        - min (float)
        - max (float)
        - std (float)
    """
    total_pixel_count = int(diff_array.size)
    valid_mask = np.isfinite(diff_array) & (~np.isnan(diff_array)) & (~np.isclose(diff_array, nodata))
    valid_pixel_count = int(np.count_nonzero(valid_mask))
    invalid_pixel_count = total_pixel_count - valid_pixel_count

    if valid_pixel_count == 0:
        return {
            "valid_pixel_count": 0,
            "invalid_pixel_count": invalid_pixel_count,
            "total_pixel_count": total_pixel_count,
            "mean": float("nan"),
            "median": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
            "std": float("nan"),
        }

    valid_vals = diff_array[valid_mask]

    return {
        "valid_pixel_count": valid_pixel_count,
        "invalid_pixel_count": invalid_pixel_count,
        "total_pixel_count": total_pixel_count,
        "mean": float(np.mean(valid_vals)),
        "median": float(np.median(valid_vals)),
        "min": float(np.min(valid_vals)),
        "max": float(np.max(valid_vals)),
        # Population standard deviation (ddof=0)
        "std": float(np.std(valid_vals)),
    }
