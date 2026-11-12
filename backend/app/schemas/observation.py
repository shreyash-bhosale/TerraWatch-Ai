from typing import Any, Dict, List, Optional
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
    product_name: Optional[str] = None
    polarization: Optional[str] = None
    frequency_band: Optional[str] = None
    orbit_direction: Optional[str] = None
    processing_level: Optional[str] = None
    measurement_units: Optional[str] = None
    resolution: Optional[float] = None
    crs: Optional[str] = None
    source_metadata: Optional[Dict[str, Any]] = None

class ObservationSearchRequest(BaseModel):
    aoi: GeoJSONPolygonGeometry
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class ObservationSearchResponse(BaseModel):
    observations: List[Observation]
    warnings: List[str] = []

class ObservationListResponse(BaseModel):
    observations: List[Observation]
    total: int

