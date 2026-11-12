from typing import Any, Literal

from pydantic import BaseModel, Field


class GeoJSONPolygonGeometry(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[list[float]]] = Field(
        ...,
        description="Array of linear rings in [longitude, latitude] coordinates. Outer ring first, closed.",
    )

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None

class ErrorEnvelope(BaseModel):
    error: ErrorDetail

