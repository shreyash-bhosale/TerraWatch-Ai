from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from app.schemas.common import GeoJSONPolygonGeometry

class RuleResult(BaseModel):
    id: str
    severity: Literal["error", "warning"]
    passed: bool
    message: str

class ObservationOrder(BaseModel):
    before_id: str
    after_id: str

class ValidateRequest(BaseModel):
    before_id: str
    after_id: str
    aoi: GeoJSONPolygonGeometry

class ValidateResponse(BaseModel):
    compatible: bool
    rules: List[RuleResult]
    order: ObservationOrder

class JobCreateRequest(BaseModel):
    before_id: str
    after_id: str
    aoi: GeoJSONPolygonGeometry

class JobCreateResponse(BaseModel):
    job_id: str
    status: Literal["queued"] = "queued"

class JobError(BaseModel):
    code: str
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    stage: Literal[
        "queued",
        "validating",
        "reading",
        "aligning",
        "differencing",
        "statistics",
        "exporting",
        "completed",
        "failed",
    ]
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    before_id: str
    after_id: str
    synthetic: bool
    error: Optional[JobError] = None

class Stats(BaseModel):
    valid_pixel_count: int
    invalid_pixel_count: int
    total_pixel_count: int
    mean: float
    median: float
    min: float
    max: float
    std: float

class LayerUrls(BaseModel):
    difference_png: str
    before_png: str
    after_png: str

class JobResultsResponse(BaseModel):
    statistics: Stats
    bounds: List[float] = Field(..., description="[west, south, east, north] in EPSG:4326")
    layers: LayerUrls
    geotiff_url: str
    metadata: Dict[str, Any]
    limitations: List[str]
    synthetic: bool

