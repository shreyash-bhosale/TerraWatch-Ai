from fastapi import FastAPI, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

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


@app.middleware("http")
async def enforce_max_body_size(request: Request, call_next):
    max_bytes = settings.MAX_BODY_BYTES
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > max_bytes:
                return JSONResponse(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    content={
                        "error": {
                            "code": "INVALID_REQUEST",
                            "message": f"Request body exceeds maximum allowed size ({max_bytes} bytes)",
                            "details": {"max_body_bytes": max_bytes},
                        }
                    },
                )
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "Invalid Content-Length header",
                        "details": None,
                    }
                },
            )

    body = await request.body()
    if len(body) > max_bytes:
        return JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": f"Request body exceeds maximum allowed size ({max_bytes} bytes)",
                    "details": {"max_body_bytes": max_bytes},
                }
            },
        )
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "INVALID_REQUEST",
                "message": "Request validation failed",
                "details": jsonable_encoder(exc.errors()),
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "INVALID_REQUEST",
                "message": str(exc.detail or "HTTP error"),
                "details": None,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, _exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "details": None,
            }
        },
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

    is_healthy = data_dir_ok and fixtures_ok
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

