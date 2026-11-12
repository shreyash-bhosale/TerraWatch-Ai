from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from app.api.helpers import call_provider, fetch_observation, resolve_provider
from app.providers.registry import get_provider
from app.schemas.common import ErrorEnvelope
from app.schemas.observation import (
    Observation,
    ObservationListResponse,
    ObservationSearchRequest,
    ObservationSearchResponse,
)
from app.services.validator import validate_aoi_geometry

router = APIRouter(prefix="/api/observations", tags=["observations"])


@router.post(
    "/search",
    response_model=ObservationSearchResponse,
    responses={
        422: {"model": ErrorEnvelope, "description": "Invalid geometry or search query"},
        502: {"model": ErrorEnvelope, "description": "Provider error"},
        503: {"model": ErrorEnvelope, "description": "Provider not available"},
    },
)
def search_observations(request: ObservationSearchRequest):
    # Validate AOI
    try:
        validate_aoi_geometry(request.aoi)
    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": "INVALID_GEOMETRY", "message": str(e), "details": None}},
        )

    provider = resolve_provider(get_provider)
    if isinstance(provider, JSONResponse):
        return provider

    result = call_provider(
        lambda: provider.search(
            aoi=request.aoi,
            start_date=request.start_date,
            end_date=request.end_date,
        )
    )
    if isinstance(result, JSONResponse):
        return result
    observations, warnings = result
    return ObservationSearchResponse(observations=observations, warnings=warnings)


@router.get(
    "",
    response_model=ObservationListResponse,
    responses={
        502: {"model": ErrorEnvelope, "description": "Provider error"},
        503: {"model": ErrorEnvelope, "description": "Provider not available"},
    },
)
def list_observations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    provider = resolve_provider(get_provider)
    if isinstance(provider, JSONResponse):
        return provider

    result = call_provider(lambda: provider.list(limit=limit, offset=offset))
    if isinstance(result, JSONResponse):
        return result
    observations, total = result
    return ObservationListResponse(observations=observations, total=total)


@router.get(
    "/{id}",
    response_model=Observation,
    responses={
        403: {"model": ErrorEnvelope, "description": "Path traversal or forbidden ID"},
        404: {"model": ErrorEnvelope, "description": "Observation not found"},
        502: {"model": ErrorEnvelope, "description": "Provider error"},
        503: {"model": ErrorEnvelope, "description": "Provider not available"},
    },
)
def get_observation(id: str):
    provider = resolve_provider(get_provider)
    if isinstance(provider, JSONResponse):
        return provider

    return fetch_observation(provider, id)
