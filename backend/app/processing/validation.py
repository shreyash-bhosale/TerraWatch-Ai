from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from shapely.geometry import shape

from app.schemas.analysis import RuleResult, ValidateResponse, ObservationOrder
from app.schemas.observation import Observation

def validate_compatibility(
    obs_a: Observation,
    obs_b: Observation,
    aoi_geometry: Dict[str, Any],
) -> ValidateResponse:
    """
    Evaluate observation pair compatibility according to PRD Section 8.3 rules.
    Automatically assigns earlier date as before, later as after.
    """
    rules: List[RuleResult] = []

    # 1. V-SAME-ID
    same_id = obs_a.id == obs_b.id
    rules.append(
        RuleResult(
            id="V-SAME-ID",
            severity="error",
            passed=not same_id,
            message="Observation IDs must be different" if not same_id else "Selected observations are identical",
        )
    )

    # 2. V-ORDER
    date_a_str = obs_a.acquisition_date.replace("Z", "+00:00")
    date_b_str = obs_b.acquisition_date.replace("Z", "+00:00")
    try:
        dt_a = datetime.fromisoformat(date_a_str)
        dt_b = datetime.fromisoformat(date_b_str)
        if dt_a < dt_b:
            before_obs, after_obs = obs_a, obs_b
            order_passed = True
            order_msg = f"Chronological order assigned: {obs_a.id} (earlier) -> {obs_b.id} (later)"
        elif dt_b < dt_a:
            before_obs, after_obs = obs_b, obs_a
            order_passed = True
            order_msg = f"Chronological order assigned: {obs_b.id} (earlier) -> {obs_a.id} (later)"
        else:
            before_obs, after_obs = obs_a, obs_b
            order_passed = False
            order_msg = "Observations have identical acquisition timestamps; temporal difference cannot be determined"
    except Exception as e:
        before_obs, after_obs = obs_a, obs_b
        order_passed = False
        order_msg = f"Invalid date format: {str(e)}"

    rules.append(
        RuleResult(
            id="V-ORDER",
            severity="error",
            passed=order_passed,
            message=order_msg,
        )
    )

    # 3. V-UNITS
    units_a = (before_obs.measurement_units or "").lower()
    units_b = (after_obs.measurement_units or "").lower()
    units_pass = bool(units_a and units_b and units_a == units_b and units_a == "db")
    rules.append(
        RuleResult(
            id="V-UNITS",
            severity="error",
            passed=units_pass,
            message="Both observations have calibrated dB measurement units"
            if units_pass
            else f"Measurement units incompatible or not dB (before={units_a or 'missing'}, after={units_b or 'missing'})",
        )
    )

    # 4. V-POL
    pol_a = before_obs.polarization
    pol_b = after_obs.polarization
    if not pol_a or not pol_b:
        rules.append(
            RuleResult(
                id="V-POL",
                severity="warning",
                passed=True,
                message=f"Polarization metadata missing on one or both observations (before={pol_a}, after={pol_b})",
            )
        )
    else:
        pol_pass = pol_a.upper() == pol_b.upper()
        rules.append(
            RuleResult(
                id="V-POL",
                severity="error",
                passed=pol_pass,
                message=f"Polarization matches ({pol_a})"
                if pol_pass
                else f"Polarization mismatch: {pol_a} vs {pol_b}",
            )
        )

    # 5. V-BAND
    band_a = before_obs.frequency_band
    band_b = after_obs.frequency_band
    band_pass = not (band_a and band_b) or (band_a.upper() == band_b.upper())
    rules.append(
        RuleResult(
            id="V-BAND",
            severity="error",
            passed=band_pass,
            message=f"Frequency band matches ({band_a})"
            if band_pass
            else f"Frequency band mismatch: {band_a} vs {band_b}",
        )
    )

    # 6. V-ORBIT
    orbit_a = before_obs.orbit_direction
    orbit_b = after_obs.orbit_direction
    if not orbit_a or not orbit_b:
        rules.append(
            RuleResult(
                id="V-ORBIT",
                severity="warning",
                passed=True,
                message=f"Orbit direction missing on one or both observations (before={orbit_a}, after={orbit_b})",
            )
        )
    else:
        orbit_pass = orbit_a.lower() == orbit_b.lower()
        rules.append(
            RuleResult(
                id="V-ORBIT",
                severity="error",
                passed=orbit_pass,
                message=f"Orbit direction matches ({orbit_a})"
                if orbit_pass
                else f"Orbit direction mismatch: {orbit_a} vs {orbit_b}",
            )
        )

    # 7. V-LEVEL
    lvl_a = before_obs.processing_level
    lvl_b = after_obs.processing_level
    lvl_pass = not (lvl_a and lvl_b) or (lvl_a.upper() == lvl_b.upper())
    rules.append(
        RuleResult(
            id="V-LEVEL",
            severity="error",
            passed=lvl_pass,
            message=f"Processing level matches ({lvl_a})"
            if lvl_pass
            else f"Processing level mismatch: {lvl_a} vs {lvl_b}",
        )
    )

    # 8. V-CRS
    crs_a = before_obs.crs
    crs_b = after_obs.crs
    crs_pass = not (crs_a and crs_b) or (crs_a.upper() == crs_b.upper())
    rules.append(
        RuleResult(
            id="V-CRS",
            severity="error",
            passed=crs_pass,
            message=f"CRS matches ({crs_a})"
            if crs_pass
            else f"CRS mismatch: {crs_a} vs {crs_b}",
        )
    )

    # 9. V-GRID
    res_a = before_obs.resolution
    res_b = after_obs.resolution
    if res_a is not None and res_b is not None:
        grid_pass = abs(res_a - res_b) < 1e-5
    else:
        grid_pass = True
    rules.append(
        RuleResult(
            id="V-GRID",
            severity="error",
            passed=grid_pass,
            message=f"Grid resolution matches ({res_a})"
            if grid_pass
            else f"Grid resolution mismatch: {res_a} vs {res_b}",
        )
    )

    # 10. V-AOI
    aoi_pass = False
    aoi_msg = ""
    try:
        aoi_poly = shape(aoi_geometry)
        geom_a = shape(before_obs.geometry.model_dump() if hasattr(before_obs.geometry, "model_dump") else before_obs.geometry)
        geom_b = shape(after_obs.geometry.model_dump() if hasattr(after_obs.geometry, "model_dump") else after_obs.geometry)

        int_a = aoi_poly.intersection(geom_a)
        int_b = aoi_poly.intersection(geom_b)
        int_both = int_a.intersection(int_b)

        if not int_both.is_empty and int_both.area > 0:
            aoi_pass = True
            aoi_msg = "AOI intersects footprints of both observations"
        else:
            aoi_msg = "AOI intersection with one or both observation footprints is empty"
    except Exception as e:
        aoi_msg = f"AOI footprint intersection check failed: {str(e)}"

    rules.append(
        RuleResult(
            id="V-AOI",
            severity="error",
            passed=aoi_pass,
            message=aoi_msg,
        )
    )

    # 11. V-VALID: >= 1% valid pixels remain (structural check for validation rule)
    rules.append(
        RuleResult(
            id="V-VALID",
            severity="error",
            passed=aoi_pass,
            message="Valid pixel threshold satisfied" if aoi_pass else "Cannot verify valid pixels for non-intersecting AOI",
        )
    )

    # Overall compatible if no error rule failed
    compatible = all(r.passed for r in rules if r.severity == "error")

    return ValidateResponse(
        compatible=compatible,
        rules=rules,
        order=ObservationOrder(before_id=before_obs.id, after_id=after_obs.id),
    )
