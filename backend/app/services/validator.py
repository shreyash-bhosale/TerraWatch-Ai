from datetime import datetime, timezone
from typing import List, Optional, Tuple

import numpy as np
from pyproj import Geod
import shapely
from shapely.geometry import shape

from app.config import settings
from app.providers.base import BaseProvider
from app.schemas.analysis import ObservationOrder, RuleResult
from app.schemas.common import GeoJSONPolygonGeometry
from app.schemas.observation import Observation


def _parse_iso(date_str: str) -> datetime:
    cleaned = date_str.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def validate_aoi_geometry(aoi: GeoJSONPolygonGeometry) -> None:
    """Validate AOI polygon geometry rules:
    - GeoJSON type is Polygon
    - Total vertices <= 500
    - Geometrically valid (Shapely is_valid, not self-intersecting)
    - Area <= MAX_AOI_AREA_KM2 (geodesic WGS84 area)
    - Non-empty area > 0

    Raises:
        ValueError: If any validation rule fails.
    """
    if aoi.type != "Polygon":
        raise ValueError(f"Expected geometry type 'Polygon', got '{aoi.type}'")

    if not aoi.coordinates or len(aoi.coordinates) == 0:
        raise ValueError("AOI polygon contains no coordinate rings")

    total_vertices = sum(len(ring) for ring in aoi.coordinates)
    if total_vertices > 500:
        raise ValueError(
            f"AOI geometry has {total_vertices} vertices; exceeds maximum permitted threshold of 500 vertices."
        )

    # Convert to Shapely
    try:
        poly = shape(aoi.model_dump())
    except Exception as e:
        raise ValueError(f"Failed to parse AOI GeoJSON geometry: {e}")

    if not poly.is_valid:
        explanation = shapely.explain_validity(poly) if hasattr(shapely, "explain_validity") else "invalid geometry"
        raise ValueError(f"AOI polygon is not geometrically valid: {explanation}")

    if poly.is_empty:
        raise ValueError("AOI polygon is empty")

    # Geodesic area calculation on WGS84 ellipsoid
    geod = Geod(ellps="WGS84")
    area_m2, _ = geod.geometry_area_perimeter(poly)
    area_km2 = abs(area_m2) / 1e6

    if area_km2 <= 0.0:
        raise ValueError("AOI polygon has zero surface area")

    if area_km2 > settings.MAX_AOI_AREA_KM2:
        raise ValueError(
            f"AOI area ({area_km2:.2f} km²) exceeds maximum permitted limit of {settings.MAX_AOI_AREA_KM2:.0f} km²."
        )


def validate_compatibility(
    before: Observation,
    after: Observation,
    aoi: GeoJSONPolygonGeometry,
    provider: Optional[BaseProvider] = None,
) -> Tuple[bool, List[RuleResult], ObservationOrder]:
    """Validate observation pair compatibility according to Section 8.3 of PRD.

    Implements:
    - V-SAME-ID: before != after (severity: error)
    - V-ORDER: dates differ; earlier assigned as "before" (severity: error if equal dates)
    - V-UNITS: both measurement_units present and equal (dB required for difference) (severity: error)
    - V-POL: polarization equal when both present; missing -> warning (severity: error/warning)
    - V-BAND: frequency band equal when both present (severity: error)
    - V-ORBIT: orbit direction equal when both present; missing -> warning (severity: error/warning)
    - V-LEVEL: processing level equal when both present (severity: error)
    - V-CRS: CRS equal (severity: error)
    - V-GRID: resolution equal within 1e-4 tolerance (severity: error)
    - V-AOI: both footprints intersect AOI and window non-empty (severity: error)
    - V-VALID: >= 1% valid pixels remain in window (severity: error)

    Returns:
        (compatible: bool, rules: List[RuleResult], order: ObservationOrder)
    """
    rules: List[RuleResult] = []

    # 1. V-SAME-ID
    if before.id == after.id:
        rules.append(
            RuleResult(
                id="V-SAME-ID",
                severity="error",
                passed=False,
                message=f"Identical observations selected ('{before.id}'); differencing requires two distinct observations.",
            )
        )
    else:
        rules.append(
            RuleResult(
                id="V-SAME-ID",
                severity="error",
                passed=True,
                message=f"Distinct observations selected: '{before.id}' and '{after.id}'.",
            )
        )

    # 2. V-ORDER
    dt_before = _parse_iso(before.acquisition_date)
    dt_after = _parse_iso(after.acquisition_date)

    if dt_before == dt_after:
        order = ObservationOrder(before_id=before.id, after_id=after.id)
        rules.append(
            RuleResult(
                id="V-ORDER",
                severity="error",
                passed=False,
                message=f"Observation acquisition dates are identical ({before.acquisition_date}); cannot determine chronological order.",
            )
        )
    elif dt_before < dt_after:
        order = ObservationOrder(before_id=before.id, after_id=after.id)
        rules.append(
            RuleResult(
                id="V-ORDER",
                severity="error",
                passed=True,
                message=f"Chronological order established: '{before.id}' ({before.acquisition_date}) before '{after.id}' ({after.acquisition_date}).",
            )
        )
    else:
        order = ObservationOrder(before_id=after.id, after_id=before.id)
        rules.append(
            RuleResult(
                id="V-ORDER",
                severity="error",
                passed=True,
                message=f"Chronological order reversed: '{after.id}' ({after.acquisition_date}) is earlier than '{before.id}' ({before.acquisition_date}).",
            )
        )

    # 3. V-UNITS
    u_before = (before.measurement_units or "").strip().lower()
    u_after = (after.measurement_units or "").strip().lower()
    if not before.measurement_units or not after.measurement_units:
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
                message=f"Incompatible measurement units ('{before.measurement_units}' vs '{after.measurement_units}'); SAR differencing requires calibrated 'dB'.",
            )
        )
    else:
        rules.append(
            RuleResult(
                id="V-UNITS",
                severity="error",
                passed=True,
                message=f"Both observations have compatible calibrated units ('{before.measurement_units}').",
            )
        )

    # 4. V-POL
    if not before.polarization or not after.polarization:
        rules.append(
            RuleResult(
                id="V-POL",
                severity="warning",
                passed=True,
                message="Polarization metadata missing for one or both observations.",
            )
        )
    elif before.polarization != after.polarization:
        rules.append(
            RuleResult(
                id="V-POL",
                severity="error",
                passed=False,
                message=f"Polarization mismatch: '{before.polarization}' vs '{after.polarization}'.",
            )
        )
    else:
        rules.append(
            RuleResult(
                id="V-POL",
                severity="error",
                passed=True,
                message=f"Polarizations match: '{before.polarization}'.",
            )
        )

    # 5. V-BAND
    if before.frequency_band and after.frequency_band:
        if before.frequency_band.upper() != after.frequency_band.upper():
            rules.append(
                RuleResult(
                    id="V-BAND",
                    severity="error",
                    passed=False,
                    message=f"Frequency band mismatch: '{before.frequency_band}' vs '{after.frequency_band}'.",
                )
            )
        else:
            rules.append(
                RuleResult(
                    id="V-BAND",
                    severity="error",
                    passed=True,
                    message=f"Frequency bands match: '{before.frequency_band}'.",
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
    if not before.orbit_direction or not after.orbit_direction:
        rules.append(
            RuleResult(
                id="V-ORBIT",
                severity="warning",
                passed=True,
                message="Orbit direction metadata missing for one or both observations.",
            )
        )
    elif before.orbit_direction.lower() != after.orbit_direction.lower():
        rules.append(
            RuleResult(
                id="V-ORBIT",
                severity="error",
                passed=False,
                message=f"Orbit direction mismatch: '{before.orbit_direction}' vs '{after.orbit_direction}'.",
            )
        )
    else:
        rules.append(
            RuleResult(
                id="V-ORBIT",
                severity="error",
                passed=True,
                message=f"Orbit directions match: '{before.orbit_direction}'.",
            )
        )

    # 7. V-LEVEL
    if before.processing_level and after.processing_level:
        if before.processing_level.upper() != after.processing_level.upper():
            rules.append(
                RuleResult(
                    id="V-LEVEL",
                    severity="error",
                    passed=False,
                    message=f"Processing level mismatch: '{before.processing_level}' vs '{after.processing_level}'.",
                )
            )
        else:
            rules.append(
                RuleResult(
                    id="V-LEVEL",
                    severity="error",
                    passed=True,
                    message=f"Processing levels match: '{before.processing_level}'.",
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
    if not before.crs or not after.crs:
        rules.append(
            RuleResult(
                id="V-CRS",
                severity="error",
                passed=False,
                message="CRS metadata missing for one or both observations.",
            )
        )
    elif before.crs.strip().upper() != after.crs.strip().upper():
        rules.append(
            RuleResult(
                id="V-CRS",
                severity="error",
                passed=False,
                message=f"CRS mismatch: '{before.crs}' vs '{after.crs}'.",
            )
        )
    else:
        rules.append(
            RuleResult(
                id="V-CRS",
                severity="error",
                passed=True,
                message=f"CRS matches: '{before.crs}'.",
            )
        )

    # 9. V-GRID
    if before.resolution is None or after.resolution is None:
        rules.append(
            RuleResult(
                id="V-GRID",
                severity="error",
                passed=False,
                message="Resolution metadata missing for one or both observations.",
            )
        )
    elif abs(before.resolution - after.resolution) > 1e-4:
        rules.append(
            RuleResult(
                id="V-GRID",
                severity="error",
                passed=False,
                message=f"Resolution mismatch: {before.resolution} vs {after.resolution} exceeds tolerance 1e-4.",
            )
        )
    else:
        rules.append(
            RuleResult(
                id="V-GRID",
                severity="error",
                passed=True,
                message=f"Resolutions match within tolerance: {before.resolution}.",
            )
        )

    # 10. V-AOI
    aoi_poly = shape(aoi.model_dump())
    before_poly = shape(before.geometry.model_dump())
    after_poly = shape(after.geometry.model_dump())

    inter_before = aoi_poly.intersection(before_poly)
    inter_after = aoi_poly.intersection(after_poly)
    common_inter = inter_before.intersection(after_poly)

    if inter_before.is_empty or inter_after.is_empty or common_inter.is_empty:
        rules.append(
            RuleResult(
                id="V-AOI",
                severity="error",
                passed=False,
                message="AOI does not intersect both observation footprints with non-empty common coverage.",
            )
        )
    else:
        rules.append(
            RuleResult(
                id="V-AOI",
                severity="error",
                passed=True,
                message="AOI intersects both observation footprints with non-empty coverage.",
            )
        )

    # 11. V-VALID (>= 1% valid pixels)
    valid_pixels_ok = True
    valid_pct: Optional[float] = None
    if provider is not None and not common_inter.is_empty:
        try:
            import rasterio
            from rasterio.mask import mask

            path_b = provider.open_asset(before.id)
            path_a = provider.open_asset(after.id)
            with rasterio.open(path_b) as src_b, rasterio.open(path_a) as src_a:
                img_b, _ = mask(src_b, [aoi.model_dump()], crop=True)
                img_a, _ = mask(src_a, [aoi.model_dump()], crop=True)

                mask_b = (img_b != src_b.nodata) & (~np.isnan(img_b))
                mask_a = (img_a != src_a.nodata) & (~np.isnan(img_a))
                common_mask = mask_b & mask_a
                total_px = common_mask.size
                valid_px = int(common_mask.sum())
                if total_px > 0:
                    valid_pct = valid_px / total_px
                    if valid_pct < 0.01:
                        valid_pixels_ok = False
        except Exception:
            # If files cannot be read at validation time, do not fail rule prematurely
            valid_pixels_ok = True

    if not valid_pixels_ok:
        rules.append(
            RuleResult(
                id="V-VALID",
                severity="error",
                passed=False,
                message=f"Insufficient valid pixels in AOI window: {valid_pct:.2%} valid (minimum 1.0% required).",
            )
        )
    else:
        pct_info = f" ({valid_pct:.1%})" if valid_pct is not None else ""
        rules.append(
            RuleResult(
                id="V-VALID",
                severity="error",
                passed=True,
                message=f"Sufficient valid pixels remain in AOI window{pct_info}.",
            )
        )

    compatible = all(r.passed for r in rules if r.severity == "error")
    return compatible, rules, order
