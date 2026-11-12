import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import matplotlib
import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import Affine, array_bounds
from rasterio.warp import transform_bounds

LIMITATIONS_NOTICE: List[str] = [
    "Difference of calibrated SAR backscatter (dB) between two dates; it is not a classified event map.",
    "Changes may come from surface change, soil moisture, vegetation, wind, incidence angle, speckle, or processing differences.",
    "No threshold or classification has been applied.",
]

SYNTHETIC_LIMITATION: str = "DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS. No real-world conclusion can be drawn."

def render_colorized_png(
    data: np.ndarray,
    vmin: float,
    vmax: float,
    cmap_name: str,
    output_path: Path,
    nodata: float = -9999.0,
) -> None:
    """
    Render 2D float array to colorized RGBA PNG with alpha=0 for invalid / nodata pixels.
    """
    valid = np.isfinite(data) & (~np.isnan(data)) & (~np.isclose(data, nodata))
    normed = np.zeros_like(data, dtype=np.float32)

    if vmax > vmin:
        normed[valid] = np.clip((data[valid] - vmin) / (vmax - vmin), 0.0, 1.0)
    else:
        normed[valid] = 0.5

    cmap = matplotlib.colormaps[cmap_name]
    rgba = cmap(normed)  # (H, W, 4) in [0.0, 1.0]
    rgba_uint8 = (rgba * 255).astype(np.uint8)
    rgba_uint8[~valid, 3] = 0  # Zero alpha (transparent) for nodata

    img = Image.fromarray(rgba_uint8, mode="RGBA")
    img.save(output_path, format="PNG")

def export_results(
    diff_array: np.ndarray,
    transform: Affine,
    crs: Any,
    stats: Dict[str, Any],
    metadata: Dict[str, Any],
    output_dir: Path,
    before_array: Optional[np.ndarray] = None,
    after_array: Optional[np.ndarray] = None,
    nodata: float = -9999.0,
) -> Dict[str, Any]:
    """
    Export processing outputs:
    - GeoTIFF: difference.tif (LZW compressed, nodata=-9999.0)
    - statistics.json
    - metadata.json (limitations, color scales, synthetic label)
    - colorized PNG overlays (difference.png, before.png, after.png)
    - bounds [west, south, east, north] in EPSG:4326

    Returns:
        Dict containing exported paths, bounds, stats, metadata, and limitations.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    height, width = diff_array.shape

    # 1. Export GeoTIFF (difference.tif)
    geotiff_path = out_dir / "difference.tif"
    tif_array = np.where(np.isnan(diff_array), nodata, diff_array).astype(np.float32)

    with rasterio.open(
        geotiff_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=nodata,
        compress="lzw",
    ) as dst:
        dst.write(tif_array, 1)

    # 2. Compute bounds in EPSG:4326
    west, south, east, north = array_bounds(height, width, transform)
    if crs and str(crs).upper() != "EPSG:4326":
        w_4326, s_4326, e_4326, n_4326 = transform_bounds(crs, "EPSG:4326", west, south, east, north)
        bounds = [float(w_4326), float(s_4326), float(e_4326), float(n_4326)]
    else:
        bounds = [float(west), float(south), float(east), float(north)]

    # 3. Determine color scale for difference
    valid_diff = diff_array[np.isfinite(diff_array) & (~np.isnan(diff_array)) & (~np.isclose(diff_array, nodata))]
    if len(valid_diff) > 0:
        p2 = float(np.percentile(valid_diff, 2))
        p98 = float(np.percentile(valid_diff, 98))
        vmax = float(max(abs(p2), abs(p98)))
        if vmax == 0.0:
            vmax = 1.0
    else:
        vmax = 1.0
        p2, p98 = -1.0, 1.0
    vmin = -vmax

    diff_color_scale = {
        "type": "diverging",
        "symmetric": True,
        "vmin": vmin,
        "vmax": vmax,
        "p2": p2,
        "p98": p98,
        "units": "dB",
        "colormap": "coolwarm",
    }

    # 4. Render colorized PNG overlays
    diff_png_path = out_dir / "difference.png"
    render_colorized_png(diff_array, vmin, vmax, "coolwarm", diff_png_path, nodata=nodata)

    before_png_path = None
    before_color_scale = None
    if before_array is not None:
        before_png_path = out_dir / "before.png"
        val_b = before_array[np.isfinite(before_array) & (~np.isnan(before_array)) & (~np.isclose(before_array, nodata))]
        b_min = float(np.min(val_b)) if len(val_b) > 0 else -30.0
        b_max = float(np.max(val_b)) if len(val_b) > 0 else 0.0
        if b_min == b_max:
            b_max = b_min + 1.0
        before_color_scale = {"vmin": b_min, "vmax": b_max, "units": "dB", "colormap": "gray"}
        render_colorized_png(before_array, b_min, b_max, "gray", before_png_path, nodata=nodata)

    after_png_path = None
    after_color_scale = None
    if after_array is not None:
        after_png_path = out_dir / "after.png"
        val_a = after_array[np.isfinite(after_array) & (~np.isnan(after_array)) & (~np.isclose(after_array, nodata))]
        a_min = float(np.min(val_a)) if len(val_a) > 0 else -30.0
        a_max = float(np.max(val_a)) if len(val_a) > 0 else 0.0
        if a_min == a_max:
            a_max = a_min + 1.0
        after_color_scale = {"vmin": a_min, "vmax": a_max, "units": "dB", "colormap": "gray"}
        render_colorized_png(after_array, a_min, a_max, "gray", after_png_path, nodata=nodata)

    # 5. Build and export statistics.json
    stats_path = out_dir / "statistics.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    # 6. Build limitations list and export metadata.json
    is_synthetic = bool(metadata.get("synthetic", False))
    limitations = list(LIMITATIONS_NOTICE)
    if is_synthetic:
        limitations.append(SYNTHETIC_LIMITATION)

    metadata_payload = {
        "synthetic": is_synthetic,
        "label": SYNTHETIC_LIMITATION if is_synthetic else "REAL OBSERVATION",
        "limitations": limitations,
        "bounds": bounds,
        "color_scales": {
            "difference": diff_color_scale,
            "before": before_color_scale,
            "after": after_color_scale,
        },
        "statistics": stats,
        "source_metadata": metadata,
    }

    meta_path = out_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata_payload, f, indent=2)

    return {
        "geotiff_path": str(geotiff_path),
        "statistics_path": str(stats_path),
        "metadata_path": str(meta_path),
        "difference_png_path": str(diff_png_path),
        "before_png_path": str(before_png_path) if before_png_path else None,
        "after_png_path": str(after_png_path) if after_png_path else None,
        "bounds": bounds,
        "statistics": stats,
        "metadata": metadata_payload,
        "limitations": limitations,
        "synthetic": is_synthetic,
    }
