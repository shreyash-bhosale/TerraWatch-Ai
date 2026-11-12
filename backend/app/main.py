import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any

from app.config import settings
from app.api.observations import router as observations_router
from app.api.analysis import router as analysis_router

app = FastAPI(
    title="TerraWatch AI API",
    version=settings.VERSION,
    description="Provider-agnostic surface change detection API for SAR imagery",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(observations_router)
app.include_router(analysis_router)

class HealthChecks(BaseModel):
    data_dir: bool
    fixtures: bool

class HealthResponse(BaseModel):
    status: str
    version: str
    provider: str
    synthetic_mode: bool
    checks: HealthChecks

@app.get("/api/health", response_model=HealthResponse)
def get_health(response: Response):
    # Ensure data directory exists and is writable
    data_dir_ok = False
    try:
        settings.data_path.mkdir(parents=True, exist_ok=True)
        test_file = settings.data_path / ".health_check_tmp"
        test_file.touch()
        test_file.unlink()
        data_dir_ok = True
    except Exception:
        data_dir_ok = False

    # Check fixtures presence
    fixtures_ok = (settings.synthetic_data_path / "syn_before.tif").is_file() and (
        settings.synthetic_data_path / "syn_after.tif"
    ).is_file()

    synthetic_mode = settings.PROVIDER == "mock"

    is_healthy = data_dir_ok
    status_str = "ok" if is_healthy else "unhealthy"

    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=status_str,
        version=settings.VERSION,
        provider=settings.PROVIDER,
        synthetic_mode=synthetic_mode,
        checks=HealthChecks(
            data_dir=data_dir_ok,
            fixtures=fixtures_ok,
        ),
    )

