import logging

from fastapi import APIRouter, status
from fastapi.responses import FileResponse, JSONResponse

from app.api.helpers import fetch_observation, resolve_provider
from app.config import settings
from app.processing.validation import validate_compatibility
from app.providers.registry import get_provider
from app.schemas.analysis import (
    JobCreateRequest,
    JobCreateResponse,
    JobResultsResponse,
    JobStatusResponse,
    ValidateRequest,
    ValidateResponse,
)
from app.schemas.common import ErrorEnvelope
from app.services.job_manager import (
    JobNotCompletedError,
    JobNotFoundError,
    ResultNotFoundError,
    job_manager,
)
from app.services.validator import validate_aoi_geometry

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analysis"])


@router.post(
    "/api/analysis/validate",
    response_model=ValidateResponse,
    responses={
        404: {"model": ErrorEnvelope, "description": "Observation not found"},
        422: {"model": ErrorEnvelope, "description": "Incompatible observations or invalid AOI"},
        502: {"model": ErrorEnvelope, "description": "Provider error"},
    },
)
def validate_analysis_pair(request: ValidateRequest):
    # Validate AOI
    try:
        validate_aoi_geometry(request.aoi)
    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": "INVALID_GEOMETRY", "message": str(e), "details": None}},
        )

    # Provider access
    provider = resolve_provider(get_provider)
    if isinstance(provider, JSONResponse):
        return provider

    # Look up observations
    before_obs = fetch_observation(provider, request.before_id)
    if isinstance(before_obs, JSONResponse):
        return before_obs

    after_obs = fetch_observation(provider, request.after_id)
    if isinstance(after_obs, JSONResponse):
        return after_obs

    return validate_compatibility(
        obs_a=before_obs,
        obs_b=after_obs,
        aoi_geometry=request.aoi,
        provider=provider,
    )


@router.post(
    "/api/analysis",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobCreateResponse,
    responses={
        404: {"model": ErrorEnvelope, "description": "Observation not found"},
        422: {"model": ErrorEnvelope, "description": "Validation failed or incompatible pair"},
        502: {"model": ErrorEnvelope, "description": "Provider error"},
    },
)
def create_analysis_job(request: JobCreateRequest):
    # Validate AOI
    try:
        validate_aoi_geometry(request.aoi)
    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": "INVALID_GEOMETRY", "message": str(e), "details": None}},
        )

    # Provider access
    provider = resolve_provider(get_provider)
    if isinstance(provider, JSONResponse):
        return provider

    # Look up observations
    before_obs = fetch_observation(provider, request.before_id)
    if isinstance(before_obs, JSONResponse):
        return before_obs

    after_obs = fetch_observation(provider, request.after_id)
    if isinstance(after_obs, JSONResponse):
        return after_obs

    # Compatibility check
    val_res = validate_compatibility(
        obs_a=before_obs,
        obs_b=after_obs,
        aoi_geometry=request.aoi,
        provider=provider,
    )
    if not val_res.compatible:
        failed_msgs = [r.message for r in val_res.rules if not r.passed and r.severity == "error"]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "INCOMPATIBLE_OBSERVATIONS",
                    "message": f"Observations cannot be differenced: {'; '.join(failed_msgs)}",
                    "details": {"rules": [r.model_dump() for r in val_res.rules]},
                }
            },
        )

    try:
        job_id = job_manager.create_job(
            before_id=request.before_id,
            after_id=request.after_id,
            aoi=request.aoi,
            provider=provider,
        )
        return JobCreateResponse(job_id=job_id, status="queued")
    except Exception as e:
        logger.exception("Failed to create analysis job")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "INTERNAL_ERROR", "message": str(e), "details": None}},
        )


@router.get(
    "/api/analysis/{job_id}",
    response_model=JobStatusResponse,
    responses={
        404: {"model": ErrorEnvelope, "description": "Job not found"},
    },
)
def get_analysis_status(job_id: str):
    try:
        return job_manager.get_status_response(job_id)
    except JobNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "JOB_NOT_FOUND", "message": f"Job '{job_id}' not found", "details": None}},
        )


@router.get(
    "/api/analysis/{job_id}/results",
    response_model=JobResultsResponse,
    responses={
        404: {"model": ErrorEnvelope, "description": "Result not found"},
        409: {"model": ErrorEnvelope, "description": "Job not completed"},
    },
)
def get_analysis_results(job_id: str):
    try:
        return job_manager.get_results_response(job_id)
    except JobNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "JOB_NOT_FOUND", "message": f"Job '{job_id}' not found", "details": None}},
        )
    except JobNotCompletedError as e:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": "JOB_NOT_COMPLETED", "message": str(e), "details": None}},
        )
    except ResultNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "RESULT_NOT_FOUND", "message": str(e), "details": None}},
        )


@router.get("/files/outputs/{job_id}/{filename}", include_in_schema=False)
def serve_output_file(job_id: str, filename: str):
    """Serve output artifacts (PNG overlays, GeoTIFF, JSON metadata) with traversal guards."""
    if ".." in job_id or "/" in job_id or "\\" in job_id:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": {"code": "INVALID_REQUEST", "message": "Access denied: Invalid job identifier", "details": None}},
        )
    if ".." in filename or "/" in filename or "\\" in filename:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": {"code": "INVALID_REQUEST", "message": "Access denied: Invalid file name", "details": None}},
        )

    target_dir = (settings.outputs_data_path / job_id).resolve()
    file_path = (target_dir / filename).resolve()

    try:
        file_path.relative_to(settings.outputs_data_path.resolve())
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": {"code": "INVALID_REQUEST", "message": "Path traversal detected", "details": None}},
        )

    if not file_path.is_file():
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "RESULT_NOT_FOUND", "message": f"File '{filename}' not found for job '{job_id}'", "details": None}},
        )

    media_type = "application/octet-stream"
    if filename.endswith(".png"):
        media_type = "image/png"
    elif filename.endswith((".tif", ".tiff")):
        media_type = "image/tiff"
    elif filename.endswith(".json"):
        media_type = "application/json"

    return FileResponse(path=file_path, media_type=media_type)
