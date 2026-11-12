import logging
from collections.abc import Callable
from typing import TypeVar

from fastapi import status
from fastapi.responses import JSONResponse

from app.providers.base import BaseProvider
from app.schemas.observation import Observation

logger = logging.getLogger(__name__)
T = TypeVar("T")


def _provider_forbidden_or_unavailable(
    exc: NotImplementedError | PermissionError,
    permission_message: str,
) -> JSONResponse:
    if isinstance(exc, NotImplementedError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": {"code": "PROVIDER_NOT_AVAILABLE", "message": str(exc), "details": None}},
        )
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"error": {"code": "INVALID_REQUEST", "message": permission_message, "details": None}},
    )


def _provider_error_response() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "error": {
                "code": "PROVIDER_ERROR",
                "message": "The observation provider could not complete the request.",
                "details": None,
            }
        },
    )


def resolve_provider(
    provider_factory: Callable[[], BaseProvider],
) -> BaseProvider | JSONResponse:
    """Instantiate the configured provider, or return a structured error response."""
    try:
        provider = provider_factory()
        if provider is None:
            raise RuntimeError("Provider factory returned None")
        return provider
    except NotImplementedError as exc:
        return _provider_forbidden_or_unavailable(exc, "")
    except Exception:
        logger.exception("Failed to initialize provider")
        return _provider_error_response()


def call_provider(operation: Callable[[], T]) -> T | JSONResponse:
    """Run a provider query operation, mapping blocked, forbidden, and unexpected failures."""
    try:
        result = operation()
        if result is None:
            raise RuntimeError("Provider operation returned None")
        return result
    except (NotImplementedError, PermissionError) as exc:
        return _provider_forbidden_or_unavailable(exc, "Access denied: Path traversal detected")
    except Exception:
        logger.exception("Provider operation failed unexpectedly")
        return _provider_error_response()


def fetch_observation(
    provider: BaseProvider,
    observation_id: str,
) -> Observation | JSONResponse:
    """Fetch an observation by ID, mapping missing, forbidden, and provider failures."""
    try:
        observation = provider.get(observation_id)
        if observation is None:
            raise KeyError(observation_id)
        return observation
    except KeyError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "OBSERVATION_NOT_FOUND",
                    "message": f"Observation '{observation_id}' not found",
                    "details": None,
                }
            },
        )
    except (NotImplementedError, PermissionError) as exc:
        return _provider_forbidden_or_unavailable(
            exc,
            "Access denied: Invalid observation identifier",
        )
    except Exception:
        logger.exception("Failed to fetch observation '%s'", observation_id)
        return _provider_error_response()
