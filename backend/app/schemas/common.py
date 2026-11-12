from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

class GeoJSONPolygonGeometry(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: List[List[List[float]]] = Field(
        ...,
        description="Array of linear rings in [longitude, latitude] coordinates. Outer ring first, closed.",
    )

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class ErrorEnvelope(BaseModel):
    error: ErrorDetail

