from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import GeoJSONPolygonGeometry


class Observation(BaseModel):
    id: str
    provider: str
    synthetic: bool = Field(..., description="Whether this observation is synthetic demo data")
    acquisition_date: str = Field(..., description="ISO 8601 acquisition timestamp")
    geometry: GeoJSONPolygonGeometry
    asset_location: str
    asset_format: str
    product_name: str | None = None
    polarization: str | None = None
    frequency_band: str | None = None
    orbit_direction: str | None = None
    processing_level: str | None = None
    measurement_units: str | None = None
    resolution: float | None = None
    crs: str | None = None
    source_metadata: dict[str, Any] | None = None

class ObservationSearchRequest(BaseModel):
    aoi: GeoJSONPolygonGeometry
    start_date: str | None = None
    end_date: str | None = None

class ObservationSearchResponse(BaseModel):
    observations: list[Observation]
    warnings: list[str] = []

class ObservationListResponse(BaseModel):
    observations: list[Observation]
    total: int

