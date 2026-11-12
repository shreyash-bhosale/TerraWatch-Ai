#!/usr/bin/env python3
"""
Generate deterministic synthetic radar fixtures for TerraWatch AI.
Conforms strictly to Section 9 of PRD.md.
"""

import json
import os
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin

def get_output_dir() -> Path:
    repo_root = Path(__file__).resolve().parent.parent.parent
    out_dir = repo_root / "data" / "synthetic"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

def write_geotiff(
    path: Path,
    array: np.ndarray,
    transform: rasterio.Affine,
    crs: str = "EPSG:4326",
    nodata: float = -9999.0,
) -> None:
    height, width = array.shape
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(array.astype(np.float32), 1)

def main():
    out_dir = get_output_dir()
    print(f"Generating synthetic fixtures in {out_dir}...")

    # Grid parameters
    width = 64
    height = 64
    origin_lon = 73.800
    origin_lat = 18.560
    pixel_size = 0.001
    crs = "EPSG:4326"
    nodata = -9999.0

    transform_std = from_origin(origin_lon, origin_lat, pixel_size, pixel_size)
    max_lon = origin_lon + width * pixel_size   # 73.864
    min_lat = origin_lat - height * pixel_size  # 18.496

    footprint_std = {
        "type": "Polygon",
        "coordinates": [
            [
                [origin_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, origin_lat],
                [origin_lon, origin_lat],
                [origin_lon, min_lat],
            ]
        ],
    }

    # 1. syn_before.tif
    # All pixels -15.0 dB, except nodata block rows 0-3, cols 0-3
    arr_before = np.full((height, width), -15.0, dtype=np.float32)
    arr_before[0:4, 0:4] = nodata
    write_geotiff(out_dir / "syn_before.tif", arr_before, transform_std, crs=crs, nodata=nodata)

    meta_before = {
        "id": "syn_before",
        "provider": "synthetic_demo",
        "synthetic": True,
        "acquisition_date": "2026-01-01T00:00:00Z",
        "geometry": footprint_std,
        "asset_location": "syn_before.tif",
        "asset_format": "GTiff",
        "product_name": "SYNTHETIC_SAR_L_LEVEL2",
        "polarization": "HH",
        "frequency_band": "L",
        "orbit_direction": "ascending",
        "processing_level": "L2",
        "measurement_units": "dB",
        "resolution": pixel_size,
        "crs": crs,
        "source_metadata": {
            "label": "synthetic",
            "simulation_note": "DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS",
        },
    }
    with open(out_dir / "syn_before.json", "w") as f:
        json.dump(meta_before, f, indent=2)

    # 2. syn_after.tif
    # All pixels -15.0 dB, except changed block rows 20-39, cols 20-39 = -22.0 dB,
    # and nodata block rows 60-63, cols 60-63 = nodata
    arr_after = np.full((height, width), -15.0, dtype=np.float32)
    arr_after[20:40, 20:40] = -22.0
    arr_after[60:64, 60:64] = nodata
    write_geotiff(out_dir / "syn_after.tif", arr_after, transform_std, crs=crs, nodata=nodata)

    meta_after = {
        "id": "syn_after",
        "provider": "synthetic_demo",
        "synthetic": True,
        "acquisition_date": "2026-01-13T00:00:00Z",
        "geometry": footprint_std,
        "asset_location": "syn_after.tif",
        "asset_format": "GTiff",
        "product_name": "SYNTHETIC_SAR_L_LEVEL2",
        "polarization": "HH",
        "frequency_band": "L",
        "orbit_direction": "ascending",
        "processing_level": "L2",
        "measurement_units": "dB",
        "resolution": pixel_size,
        "crs": crs,
        "source_metadata": {
            "label": "synthetic",
            "simulation_note": "DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS",
        },
    }
    with open(out_dir / "syn_after.json", "w") as f:
        json.dump(meta_after, f, indent=2)

    # 3. syn_misaligned.tif (tests V-GRID)
    pixel_size_misaligned = 0.002
    transform_misaligned = from_origin(origin_lon, origin_lat, pixel_size_misaligned, pixel_size_misaligned)
    max_lon_misaligned = origin_lon + width * pixel_size_misaligned
    min_lat_misaligned = origin_lat - height * pixel_size_misaligned

    footprint_misaligned = {
        "type": "Polygon",
        "coordinates": [
            [
                [origin_lon, min_lat_misaligned],
                [max_lon_misaligned, min_lat_misaligned],
                [max_lon_misaligned, origin_lat],
                [origin_lon, origin_lat],
                [origin_lon, min_lat_misaligned],
            ]
        ],
    }
    arr_misaligned = np.full((height, width), -15.0, dtype=np.float32)
    write_geotiff(out_dir / "syn_misaligned.tif", arr_misaligned, transform_misaligned, crs=crs, nodata=nodata)

    meta_misaligned = {
        "id": "syn_misaligned",
        "provider": "synthetic_demo",
        "synthetic": True,
        "acquisition_date": "2026-01-25T00:00:00Z",
        "geometry": footprint_misaligned,
        "asset_location": "syn_misaligned.tif",
        "asset_format": "GTiff",
        "product_name": "SYNTHETIC_SAR_L_LEVEL2",
        "polarization": "HH",
        "frequency_band": "L",
        "orbit_direction": "ascending",
        "processing_level": "L2",
        "measurement_units": "dB",
        "resolution": pixel_size_misaligned,
        "crs": crs,
        "source_metadata": {
            "label": "synthetic",
            "simulation_note": "DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS",
        },
    }
    with open(out_dir / "syn_misaligned.json", "w") as f:
        json.dump(meta_misaligned, f, indent=2)

    # 4. syn_wrongunits.tif (tests V-UNITS)
    arr_wrongunits = np.full((height, width), -15.0, dtype=np.float32)
    write_geotiff(out_dir / "syn_wrongunits.tif", arr_wrongunits, transform_std, crs=crs, nodata=nodata)

    meta_wrongunits = {
        "id": "syn_wrongunits",
        "provider": "synthetic_demo",
        "synthetic": True,
        "acquisition_date": "2026-02-06T00:00:00Z",
        "geometry": footprint_std,
        "asset_location": "syn_wrongunits.tif",
        "asset_format": "GTiff",
        "product_name": "SYNTHETIC_SAR_L_LEVEL2",
        "polarization": "HH",
        "frequency_band": "L",
        "orbit_direction": "ascending",
        "processing_level": "L2",
        "measurement_units": "linear",
        "resolution": pixel_size,
        "crs": crs,
        "source_metadata": {
            "label": "synthetic",
            "simulation_note": "DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS",
        },
    }
    with open(out_dir / "syn_wrongunits.json", "w") as f:
        json.dump(meta_wrongunits, f, indent=2)

    # 5. aoi.geojson
    with open(out_dir / "aoi.geojson", "w") as f:
        json.dump(footprint_std, f, indent=2)

    # 6. expected_stats.json
    # Analytical computation matching Section 9:
    # 4064 valid pixels, 400 with -7.0 dB, 3664 with 0.0 dB
    mean_val = -2800.0 / 4064.0
    # std analytical:
    var_val = (400.0 * ((-7.0 - mean_val) ** 2) + 3664.0 * ((0.0 - mean_val) ** 2)) / 4064.0
    std_val = float(np.sqrt(var_val))

    expected_stats = {
        "valid_pixel_count": 4064,
        "invalid_pixel_count": 32,
        "total_pixel_count": 4096,
        "mean": float(mean_val),
        "median": 0.0,
        "min": -7.0,
        "max": 0.0,
        "std": std_val,
        "units": "dB",
        "label": "DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS",
    }
    with open(out_dir / "expected_stats.json", "w") as f:
        json.dump(expected_stats, f, indent=2)

    print("Successfully generated all synthetic fixtures.")

if __name__ == "__main__":
    main()

