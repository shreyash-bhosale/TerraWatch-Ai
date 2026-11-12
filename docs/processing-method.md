# TerraWatch AI — Scientific Processing Specification & Method

> Documents the exact implemented algorithms in `backend/app/processing/` and `backend/app/services/validator.py`.

## 1. Design Principles

1. **Pure unit output:** Output values represent calibrated SAR backscatter differences in decibels ($\Delta\sigma^0 = \text{after} - \text{before}\ \text{dB}$). **No flood thresholds, water masks, or semantic classifications are ever applied.**
2. **Fail loudly on incompatible inputs:** Misaligned CRS, resolutions, sub-pixel grid shifts, non-dB units, or non-overlapping extents raise explicit errors rather than silently resampling or warping rasters.
3. **Nodata isolation before math:** Nodata sentinels (default `-9999.0`), `NaN`, and `±inf` are masked to `np.nan` prior to any arithmetic or summary statistics.
4. **Honest synthetic labeling:** Any run involving a synthetic observation (`synthetic: true`) embeds `"DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS. No real-world conclusion can be drawn."` into `metadata.json` and `limitations`.

---

## 2. AOI Validation (`backend/app/services/validator.py`)

`validate_aoi_geometry` converts GeoJSON `Polygon` inputs with Shapely and enforces:
- GeoJSON `type == "Polygon"`, at least 1 linear ring, outer ring contains `>= 4` vertices (`>= 3` distinct coordinates), total vertex count `<= 500`, and ring closure (`first == last`).
- All coordinates bounded by longitude `[-180, 180]` and latitude `[-90, 90]`.
- Topological validity (`shapely_poly.is_valid` and `not shapely_poly.is_empty`).
- Geodesic surface area computed using `pyproj.Geod(ellps="WGS84").geometry_area_perimeter`, bounded by `(0, settings.MAX_AOI_AREA_KM2]` (default `50,000 km²`).

---

## 3. Compatibility Rules (`backend/app/processing/validation.py`)

`validate_compatibility` is the single source of truth called by `POST /api/analysis/validate`, `JobManager.create_job`, and `run_pipeline`. Earlier `acquisition_date` is assigned `before_id` and later `after_id`.

| Rule ID | Severity | Condition Checked | Failure / Warning Behavior |
| --- | --- | --- | --- |
| `V-SAME-ID` | `error` | `obs_a.id != obs_b.id` | Fails if same observation selected twice. |
| `V-ORDER` | `error` | Valid ISO dates and `dt_a != dt_b` | Auto-orders earlier -> `before`; fails if equal or unparseable timestamps. |
| `V-UNITS` | `error` | Both `measurement_units.lower() == "db"` | Fails if missing or non-dB (e.g. `linear`). |
| `V-POL` | `error` (miss=`warning`) | Polarization case-insensitive equality | Warns (passes) if metadata missing; fails on mismatch (e.g. `VV` vs `VH`). |
| `V-BAND` | `error` (miss=`warning`) | Frequency band equality | Warns (passes) if metadata missing; fails on mismatch (e.g. `L-band` vs `C-band`). |
| `V-ORBIT` | `error` (miss=`warning`) | Orbit direction equality | Warns (passes) if metadata missing; fails on mismatch (`ascending` vs `descending`). |
| `V-LEVEL` | `error` (miss=`warning`) | Processing level equality | Warns (passes) if metadata missing; fails on mismatch (`GCOV` vs `GRD`). |
| `V-CRS` | `error` | Both CRS present and equal | Fails if missing or mismatched (e.g. `EPSG:4326` vs `EPSG:32643`). |
| `V-GRID` | `error` | Resolution present and `abs(res_a - res_b) <= 1e-4` | Fails if missing or difference `> 1e-4`. |
| `V-AOI` | `error` | `aoi ∩ geom_a ∩ geom_b` has `area > 0` | Fails if common intersection is empty or zero-area. |
| `V-VALID` | `error` | Valid intersection pixels after AOI window & nodata mask | Fails if `< 1%` (`valid_pct < 0.01`) of pixels in AOI window are valid. |

---

## 4. Processing Pipeline (`backend/app/processing/pipeline.py`)

1. **`reading` (`readers/geotiff.py`):** Reads band 1 as `float32` into `RasterData` (`array`, `crs`, `transform`, `bounds`, `resolution`, `nodata`, `units`), wrapping corrupted/missing files in `CorruptRasterError` / `FileNotFoundError`.
2. **Compatibility check:** Invokes `validate_compatibility(...)`; failures raise `IncompatiblePipelineError` (`INCOMPATIBLE_OBSERVATIONS`).
3. **AOI Windowing & Nodata Masking (`preprocessing.py`):**
   - `compute_aoi_window` intersects the AOI bounding box with raster bounds and computes an integer pixel `rasterio.windows.Window`.
   - `mask_nodata_to_nan` copies pixel arrays to `float32` and sets `np.isclose(arr, nodata) | np.isnan(arr) | ~np.isfinite(arr)` to `np.nan`.
4. **`aligning` (`alignment.py`):**
   - `check_alignment` requires equal `crs` and matching `resolution` (`rtol=1e-4`).
   - If shape, bounds (`atol=1e-5`), and affine transform (`atol=1e-5`) match, returns inputs unchanged.
   - If extents differ with matching CRS/resolution, verifies non-empty overlap and integer pixel phase offsets (`abs(dx - round(dx)) <= 1e-3`, `abs(dy - round(dy)) <= 1e-3`), cropping both rasters to their intersection without resampling. Any violation raises `AlignmentMismatchError` (`ALIGNMENT_MISMATCH`).
5. **`differencing` (`change_detection.py`):**
   - Requires identical aligned shapes (`before.shape == after.shape`).
   - Builds `valid_mask = valid_before & valid_after` excluding nodata and non-finite pixels.
   - Computes `diff[valid_mask] = after.array[valid_mask] - before.array[valid_mask]` (`float32`), leaving invalid locations as `np.nan`.
6. **`statistics` (`statistics.py`):**
   - Computes `total_pixel_count`, `valid_pixel_count`, `invalid_pixel_count`, and over valid pixels: `mean`, `median`, `min`, `max`, `std` (or `nan` if 0 valid pixels).
7. **`exporting` (`export.py`):**
   - `difference.tif`: LZW-compressed `float32` GeoTIFF preserving aligned `crs` and `transform`, with `np.nan` mapped back to `nodata=-9999.0`.
   - `difference.png`: RGBA PNG rendered using symmetric percentiles (`p2`, `p98`, `vmax = max(|p2|, |p98|)`, clamped `>= 1.0` if 0) with matplotlib `"coolwarm"` diverging colormap centered at `0.0`, setting alpha `0` (transparent) on invalid pixels.
   - `before.png`, `after.png`: RGBA PNGs using `"viridis"` (`[min, max]`) with transparent nodata.
   - `statistics.json` & `metadata.json`: Persist summary metrics, WGS84 `bounds` (transformed via `rasterio.warp.transform_bounds` when source CRS != `EPSG:4326`), `color_scales`, `limitations`, and `synthetic` status.
   - On any exception in `run_pipeline`, partial output artifacts in `output_dir` are atomically removed and stage transitions to `failed`.
