from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

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

    # Get provider
    try:
        provider = get_provider()
    except NotImplementedError as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": {"code": "PROVIDER_NOT_AVAILABLE", "message": str(e), "details": None}},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": {"code": "PROVIDER_ERROR", "message": str(e), "details": None}},
        )

    # Execute search
    try:
        observations, warnings = provider.search(
            aoi=request.aoi,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        return ObservationSearchResponse(observations=observations, warnings=warnings)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": {"code": "PROVIDER_ERROR", "message": str(e), "details": None}},
        )


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
    try:
        provider = get_provider()
    except NotImplementedError as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": {"code": "PROVIDER_NOT_AVAILABLE", "message": str(e), "details": None}},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": {"code": "PROVIDER_ERROR", "message": str(e), "details": None}},
        )

    try:
        observations, total = provider.list(limit=limit, offset=offset)
        return ObservationListResponse(observations=observations, total=total)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": {"code": "PROVIDER_ERROR", "message": str(e), "details": None}},
        )


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
    try:
        provider = get_provider()
    except NotImplementedError as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": {"code": "PROVIDER_NOT_AVAILABLE", "message": str(e), "details": None}},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": {"code": "PROVIDER_ERROR", "message": str(e), "details": None}},
        )

    try:
        return provider.get(id)
    except KeyError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "OBSERVATION_NOT_FOUND", "message": f"Observation '{id}' not found", "details": None}},
        )
    except PermissionError as e:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": {"code": "FORBIDDEN", "message": str(e), "details": None}},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": {"code": "PROVIDER_ERROR", "message": str(e), "details": None}},
        )
