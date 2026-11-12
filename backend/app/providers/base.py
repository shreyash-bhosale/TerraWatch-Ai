from abc import ABC, abstractmethod
from pathlib import Path

from app.schemas.common import GeoJSONPolygonGeometry
from app.schemas.observation import Observation


class BaseProvider(ABC):
    """Abstract base class for all SAR observation data providers."""

    @abstractmethod
    def search(
        self,
        aoi: GeoJSONPolygonGeometry,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[Observation], list[str]]:
        """Search the provider's catalog for observations intersecting the AOI and matching date filters.

        Args:
            aoi: Area of Interest polygon in GeoJSON format (EPSG:4326).
            start_date: Optional ISO 8601 start date/timestamp filter.
            end_date: Optional ISO 8601 end date/timestamp filter.

        Returns:
            A tuple of (matching observations, list of warning messages).
        """

    @abstractmethod
    def list(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Observation], int]:
        """List all observations in the catalog with pagination.

        Args:
            limit: Maximum number of items to return.
            offset: Zero-based start index.

        Returns:
            A tuple of (observations list, total count).
        """

    @abstractmethod
    def get(self, id: str) -> Observation:
        """Retrieve a single observation by its unique identifier.

        Args:
            id: The observation ID.

        Returns:
            The normalized Observation object.

        Raises:
            KeyError: If observation is not found.
        """

    @abstractmethod
    def open_asset(self, id: str) -> Path:
        """Resolve and validate the local file path to the raster asset for an observation.

        Args:
            id: The observation ID.

        Returns:
            Absolute Path to the raster asset.

        Raises:
            KeyError: If observation is not found.
            FileNotFoundError: If the asset file does not exist on disk.
            PermissionError: If path traversal or access restriction is violated.
        """
