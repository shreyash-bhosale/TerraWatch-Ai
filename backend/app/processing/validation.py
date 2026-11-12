from datetime import UTC, datetime
from typing import Any

import numpy as np
from shapely.errors import ShapelyError
from shapely.geometry import shape

from app.processing.preprocessing import (
    AoiTransformError,
    EmptyWindowError,
    compute_aoi_window,
    get_valid_mask,
    mask_nodata_to_nan,
)
from app.processing.raster_data import RasterData
from app.processing.readers.geotiff import CorruptRasterError, GeoTIFFReader
from app.schemas.analysis import ObservationOrder, RuleResult, ValidateResponse
from app.schemas.common import GeoJSONPolygonGeometry
from app.schemas.observation import Observation


def _parse_iso(date_str: str) -> datetime:
    cleaned = date_str.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _slice_window_valid_mask(raster: RasterData, aoi_dict: dict[str, Any]) -> np.ndarray:
    window = compute_aoi_window(
        aoi_geometry=aoi_dict,
        raster_bounds=raster.bounds,
        transform=raster.transform,
        width=raster.width,
        height=raster.height,
        raster_crs=raster.crs,
    )
    r_start = int(window.row_off)
    r_end = int(window.row_off + window.height)
    c_start = int(window.col_off)
    c_end = int(window.col_off + window.width)
    cropped = raster.array[r_start:r_end, c_start:c_end]
    masked = mask_nodata_to_nan(cropped, nodata=raster.nodata)
    return get_valid_mask(masked, nodata=raster.nodata)


def _window_valid_mask(raster: RasterData) -> np.ndarray:
    masked = mask_nodata_to_nan(raster.array, nodata=raster.nodata)
    return get_valid_mask(masked, nodata=raster.nodata)


def _read_window_for_observation(
    reader: GeoTIFFReader,
    asset_path: Any,
    aoi_dict: dict[str, Any],
) -> RasterData:
    hdr = reader.read_metadata(asset_path)
    window = compute_aoi_window(
        aoi_geometry=aoi_dict,
        raster_bounds=hdr["bounds"],
        transform=hdr["transform"],
        width=hdr["width"],
        height=hdr["height"],
        raster_crs=hdr["crs"],
    )
    return reader.read(asset_path, window=window)


def _evaluate_valid_pixel_fraction(
    before_obs: Observation,
    after_obs: Observation,
    aoi_dict: dict[str, Any],
    before_raster: RasterData | None,
    after_raster: RasterData | None,
    provider: Any | None,
    rasters_pre_windowed: bool = False,
) -> tuple[bool, float | None, str | None]:
    """
    Evaluate valid pixel fraction in AOI window after nodata masking.
    Uses windowed reads when loading from a provider so full rasters are not loaded.
    Returns (passed, valid_fraction_or_none, failure_reason_or_none).
    """
    r_b = before_raster
    r_a = after_raster
    b_windowed = rasters_pre_windowed and r_b is not None
    a_windowed = rasters_pre_windowed and r_a is not None

    if (r_b is None or r_a is None) and provider is not None:
        try:
            reader = GeoTIFFReader()
            if r_b is None:
                r_b = _read_window_for_observation(reader, provider.open_asset(before_obs.id), aoi_dict)
                b_windowed = True
            if r_a is None:
                r_a = _read_window_for_observation(reader, provider.open_asset(after_obs.id), aoi_dict)
                a_windowed = True
        except (EmptyWindowError, AoiTransformError) as e:
            return False, 0.0, str(e)
        except (CorruptRasterError, FileNotFoundError, OSError):
            # Defer unreadable/corrupt file failures to the async pipeline job worker
            return True, None, None

    if r_b is None or r_a is None:
        return True, None, None

    try:
        mask_b = _window_valid_mask(r_b) if b_windowed else _slice_window_valid_mask(r_b, aoi_dict)
        mask_a = _window_valid_mask(r_a) if a_windowed else _slice_window_valid_mask(r_a, aoi_dict)
    except (EmptyWindowError, AoiTransformError) as e:
        return False, 0.0, str(e)

    if mask_b.size == 0 or mask_a.size == 0:
        return False, 0.0, "AOI data window is empty"

    if mask_b.shape == mask_a.shape:
        common = mask_b & mask_a
        total_px = int(common.size)
        valid_px = int(np.count_nonzero(common))
        valid_pct = valid_px / total_px if total_px > 0 else 0.0
    else:
        pct_b = float(np.count_nonzero(mask_b)) / float(mask_b.size)
        pct_a = float(np.count_nonzero(mask_a)) / float(mask_a.size)
        valid_pct = min(pct_b, pct_a)

    if valid_pct < 0.01:
        return False, valid_pct, None
    return True, valid_pct, None


def validate_compatibility(
    obs_a: Observation,
    obs_b: Observation,
    aoi_geometry: dict[str, Any] | GeoJSONPolygonGeometry,
    before_raster: RasterData | None = None,
    after_raster: RasterData | None = None,
    provider: Any | None = None,
    rasters_pre_windowed: bool = False,
) -> ValidateResponse:
    """
    Evaluate observation pair compatibility according to PRD Section 8.3 rules.
    Single source of truth shared by API endpoints, JobManager, and processing pipeline.
    Automatically assigns earlier date as before, later as after.
    """
    aoi_dict = aoi_geometry.model_dump() if hasattr(aoi_geometry, "model_dump") else aoi_geometry
    rules: list[RuleResult] = []

    # 1. V-SAME-ID
    same_id = obs_a.id == obs_b.id
    rules.append(
        RuleResult(
            id="V-SAME-ID",
            severity="error",
            passed=not same_id,
            message=(
                f"Distinct observations selected: '{obs_a.id}' and '{obs_b.id}'."
                if not same_id
                else f"Identical observations selected ('{obs_a.id}'); differencing requires two distinct observations."
            ),
        )
    )

    # 2. V-ORDER
    order_swapped = False
    try:
        dt_a = _parse_iso(obs_a.acquisition_date)
        dt_b = _parse_iso(obs_b.acquisition_date)
        if dt_a < dt_b:
            before_obs, after_obs = obs_a, obs_b
            order_passed = True
            order_msg = (
                f"Chronological order established: '{before_obs.id}' ({before_obs.acquisition_date}) "
                f"before '{after_obs.id}' ({after_obs.acquisition_date})."
            )
        elif dt_b < dt_a:
            before_obs, after_obs = obs_b, obs_a
            order_swapped = True
            order_passed = True
            order_msg = (
                f"Chronological order reversed: '{before_obs.id}' ({before_obs.acquisition_date}) "
                f"is earlier than '{after_obs.id}' ({after_obs.acquisition_date})."
            )
        else:
            before_obs, after_obs = obs_a, obs_b
            order_passed = False
            order_msg = (
                f"Observation acquisition dates are identical ({obs_a.acquisition_date}); "
                "cannot determine chronological order."
            )
    except (ValueError, TypeError) as e:
        before_obs, after_obs = obs_a, obs_b
        order_passed = False
        order_msg = f"Invalid acquisition date format: {e}"

    if order_swapped and before_raster is not None and after_raster is not None:
        before_raster, after_raster = after_raster, before_raster

    rules.append(
        RuleResult(
            id="V-ORDER",
            severity="error",
            passed=order_passed,
            message=order_msg,
        )
    )

    # 3. V-UNITS
    u_before = (before_obs.measurement_units or "").strip().lower()
    u_after = (after_obs.measurement_units or "").strip().lower()
    if not before_obs.measurement_units or not after_obs.measurement_units:
        rules.append(
            RuleResult(
                id="V-UNITS",
                severity="error",
                passed=False,
                message="Missing measurement_units metadata; calibrated 'dB' is required for SAR differencing.",
            )
        )
    elif u_before != "db" or u_after != "db":
        rules.append(
            RuleResult(
                id="V-UNITS",
                severity="error",
                passed=False,
                message=(
                    f"Incompatible measurement units ('{before_obs.measurement_units}' vs "
                    f"'{after_obs.measurement_units}'); SAR differencing requires calibrated 'dB'."
                ),
            )
        )
    else:
        rules.append(
            RuleResult(
                id="V-UNITS",
                severity="error",
                passed=True,
                message=f"Both observations have compatible calibrated units ('{before_obs.measurement_units}').",
            )
        )

    # 4. V-POL
    if not before_obs.polarization or not after_obs.polarization:
        rules.append(
            RuleResult(
                id="V-POL",
                severity="warning",
                passed=True,
                message="Polarization metadata missing for one or both observations.",
            )
        )
    elif before_obs.polarization.strip().upper() != after_obs.polarization.strip().upper():
        rules.append(
            RuleResult(
                id="V-POL",
                severity="error",
                passed=False,
                message=f"Polarization mismatch: '{before_obs.polarization}' vs '{after_obs.polarization}'.",
            )
        )
    else:
        rules.append(
            RuleResult(
                id="V-POL",
                severity="error",
                passed=True,
                message=f"Polarizations match: '{before_obs.polarization}'.",
            )
        )

    # 5. V-BAND
    if before_obs.frequency_band and after_obs.frequency_band:
        if before_obs.frequency_band.strip().upper() != after_obs.frequency_band.strip().upper():
            rules.append(
                RuleResult(
                    id="V-BAND",
                    severity="error",
                    passed=False,
                    message=f"Frequency band mismatch: '{before_obs.frequency_band}' vs '{after_obs.frequency_band}'.",
                )
            )
        else:
            rules.append(
                RuleResult(
                    id="V-BAND",
                    severity="error",
                    passed=True,
                    message=f"Frequency bands match: '{before_obs.frequency_band}'.",
                )
            )
    else:
        rules.append(
            RuleResult(
                id="V-BAND",
                severity="warning",
                passed=True,
                message="Frequency band metadata missing for one or both observations.",
            )
        )

    # 6. V-ORBIT
    if not before_obs.orbit_direction or not after_obs.orbit_direction:
        rules.append(
            RuleResult(
                id="V-ORBIT",
                severity="warning",
                passed=True,
                message="Orbit direction metadata missing for one or both observations.",
            )
        )
    elif before_obs.orbit_direction.strip().lower() != after_obs.orbit_direction.strip().lower():
        rules.append(
            RuleResult(
                id="V-ORBIT",
                severity="error",
                passed=False,
                message=f"Orbit direction mismatch: '{before_obs.orbit_direction}' vs '{after_obs.orbit_direction}'.",
            )
        )
    else:
        rules.append(
            RuleResult(
                id="V-ORBIT",
                severity="error",
                passed=True,
                message=f"Orbit directions match: '{before_obs.orbit_direction}'.",
            )
        )

    # 7. V-LEVEL
    if before_obs.processing_level and after_obs.processing_level:
        if before_obs.processing_level.strip().upper() != after_obs.processing_level.strip().upper():
            rules.append(
                RuleResult(
                    id="V-LEVEL",
                    severity="error",
                    passed=False,
                    message=f"Processing level mismatch: '{before_obs.processing_level}' vs '{after_obs.processing_level}'.",
                )
            )
        else:
            rules.append(
                RuleResult(
                    id="V-LEVEL",
                    severity="error",
                    passed=True,
                    message=f"Processing levels match: '{before_obs.processing_level}'.",
                )
            )
    else:
        rules.append(
            RuleResult(
                id="V-LEVEL",
                severity="warning",
                passed=True,
                message="Processing level metadata missing for one or both observations.",
            )
        )

    # 8. V-CRS
    if not before_obs.crs or not after_obs.crs:
        rules.append(
            RuleResult(
                id="V-CRS",
                severity="error",
                passed=False,
                message="CRS metadata missing for one or both observations.",
            )
        )
    elif before_obs.crs.strip().upper() != after_obs.crs.strip().upper():
        rules.append(
            RuleResult(
                id="V-CRS",
                severity="error",
                passed=False,
                message=f"CRS mismatch: '{before_obs.crs}' vs '{after_obs.crs}'.",
            )
        )
    else:
        rules.append(
            RuleResult(
                id="V-CRS",
                severity="error",
                passed=True,
                message=f"CRS matches: '{before_obs.crs}'.",
            )
        )

    # 9. V-GRID
    if before_obs.resolution is None or after_obs.resolution is None:
        rules.append(
            RuleResult(
                id="V-GRID",
                severity="error",
                passed=False,
                message="Resolution metadata missing for one or both observations.",
            )
        )
    elif abs(before_obs.resolution - after_obs.resolution) > 1e-4:
        rules.append(
            RuleResult(
                id="V-GRID",
                severity="error",
                passed=False,
                message=f"Resolution mismatch: {before_obs.resolution} vs {after_obs.resolution} exceeds tolerance 1e-4.",
            )
        )
    else:
        rules.append(
            RuleResult(
                id="V-GRID",
                severity="error",
                passed=True,
                message=f"Resolutions match within tolerance: {before_obs.resolution}.",
            )
        )

    # 10. V-AOI
    aoi_pass = False
    aoi_msg = ""
    try:
        aoi_poly = shape(aoi_dict)
        geom_a = shape(before_obs.geometry.model_dump() if hasattr(before_obs.geometry, "model_dump") else before_obs.geometry)
        geom_b = shape(after_obs.geometry.model_dump() if hasattr(after_obs.geometry, "model_dump") else after_obs.geometry)

        int_a = aoi_poly.intersection(geom_a)
        int_b = aoi_poly.intersection(geom_b)
        int_both = int_a.intersection(int_b)

        if not int_a.is_empty and not int_b.is_empty and not int_both.is_empty and int_both.area > 0:
            aoi_pass = True
            aoi_msg = "AOI intersects both observation footprints with non-empty coverage."
        else:
            aoi_msg = "AOI does not intersect both observation footprints with non-empty common coverage."
    except (ShapelyError, ValueError, TypeError, AttributeError) as e:
        aoi_msg = f"AOI footprint intersection check failed: {e}"

    # 11. V-VALID (>= 1% valid pixels after masking and AOI windowing)
    if not aoi_pass:
        valid_pixels_ok = False
        valid_pct: float | None = 0.0
        window_err: str | None = "AOI intersection is empty"
    else:
        valid_pixels_ok, valid_pct, window_err = _evaluate_valid_pixel_fraction(
            before_obs=before_obs,
            after_obs=after_obs,
            aoi_dict=aoi_dict,
            before_raster=before_raster,
            after_raster=after_raster,
            provider=provider,
            rasters_pre_windowed=rasters_pre_windowed,
        )
        if window_err is not None:
            aoi_pass = False
            aoi_msg = window_err

    rules.append(
        RuleResult(
            id="V-AOI",
            severity="error",
            passed=aoi_pass,
            message=aoi_msg,
        )
    )

    if not valid_pixels_ok:
        pct_text = f"{valid_pct:.2%}" if valid_pct is not None else "0.00%"
        valid_msg = f"Insufficient valid pixels in AOI window: {pct_text} valid (minimum 1.0% required)."
    else:
        pct_info = f" ({valid_pct:.1%})" if valid_pct is not None else ""
        valid_msg = f"Sufficient valid pixels remain in AOI window{pct_info}."

    rules.append(
        RuleResult(
            id="V-VALID",
            severity="error",
            passed=valid_pixels_ok,
            message=valid_msg,
        )
    )

    compatible = all(r.passed for r in rules if r.severity == "error")

    return ValidateResponse(
        compatible=compatible,
        rules=rules,
        order=ObservationOrder(before_id=before_obs.id, after_id=after_obs.id),
    )
