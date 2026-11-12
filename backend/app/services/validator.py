import shapely
from pyproj import Geod
from shapely.errors import ShapelyError
from shapely.geometry import shape

from app.config import settings
from app.schemas.common import GeoJSONPolygonGeometry


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

    try:
        poly = shape(aoi.model_dump())
    except (ShapelyError, ValueError, TypeError) as e:
        raise ValueError(f"Failed to parse AOI GeoJSON geometry: {e}")

    if not poly.is_valid:
        explanation = shapely.explain_validity(poly) if hasattr(shapely, "explain_validity") else "invalid geometry"
        raise ValueError(f"AOI polygon is not geometrically valid: {explanation}")

    if poly.is_empty:
        raise ValueError("AOI polygon is empty")

    geod = Geod(ellps="WGS84")
    area_m2, _ = geod.geometry_area_perimeter(poly)
    area_km2 = abs(area_m2) / 1e6

    if area_km2 <= 0.0:
        raise ValueError("AOI polygon has zero surface area")

    if area_km2 > settings.MAX_AOI_AREA_KM2:
        raise ValueError(
            f"AOI area ({area_km2:.2f} km²) exceeds maximum permitted limit of {settings.MAX_AOI_AREA_KM2:.0f} km²."
        )
