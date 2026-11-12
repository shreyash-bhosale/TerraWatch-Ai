import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from shapely.geometry import shape

from app.providers.base import BaseProvider
from app.schemas.common import GeoJSONPolygonGeometry
from app.schemas.observation import Observation

logger = logging.getLogger(__name__)


def _parse_iso_date(date_str: str, is_end_of_day: bool = False) -> datetime:
    """Parse ISO date or date-time string into a UTC datetime object."""
    cleaned = date_str.strip()
    # Normalize Z suffix to +00:00 for fromisoformat
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    
    # If string is just date (YYYY-MM-DD), append time
    if len(cleaned) == 10 and cleaned.count("-") == 2:
        if is_end_of_day:
            cleaned += "T23:59:59.999999+00:00"
        else:
            cleaned += "T00:00:00+00:00"

    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


class MockProvider(BaseProvider):
    """Mock Provider that reads synthetic SAR observations from data/synthetic.
    
    All observations returned by this provider always have synthetic=True per Rule R3.
    """

    def __init__(self, catalog_dir: Path):
        self.catalog_dir = Path(catalog_dir).resolve()

    def _load_catalog(self) -> dict[str, Observation]:
        """Load and parse all valid observation JSON sidecars in catalog_dir."""
        catalog: dict[str, Observation] = {}
        if not self.catalog_dir.is_dir():
            return catalog

        for json_path in sorted(self.catalog_dir.glob("*.json")):
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue
                # Require observation identity and footprint
                if "id" not in data or "geometry" not in data or "acquisition_date" not in data:
                    continue
                # Enforce Rule R3: synthetic is strictly True
                data["synthetic"] = True
                obs = Observation.model_validate(data)
                catalog[obs.id] = obs
            except (OSError, ValueError, TypeError) as exc:
                logger.warning("Skipping invalid mock catalog entry '%s': %s", json_path.name, exc)

        return catalog

    def search(
        self,
        aoi: GeoJSONPolygonGeometry,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[Observation], list[str]]:
        catalog = self._load_catalog()
        aoi_poly = shape(aoi.model_dump())

        start_dt = _parse_iso_date(start_date) if start_date else None
        end_dt = _parse_iso_date(end_date, is_end_of_day=True) if end_date else None

        matching: list[Observation] = []
        for obs in catalog.values():
            # Date filter
            obs_dt = _parse_iso_date(obs.acquisition_date)
            if start_dt and obs_dt < start_dt:
                continue
            if end_dt and obs_dt > end_dt:
                continue

            # Geometry intersection filter
            obs_poly = shape(obs.geometry.model_dump())
            if aoi_poly.intersects(obs_poly) and not aoi_poly.intersection(obs_poly).is_empty:
                matching.append(obs)

        # Sort by acquisition_date ascending
        matching.sort(key=lambda o: o.acquisition_date)
        return matching, []

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Observation], int]:
        catalog = self._load_catalog()
        all_obs = sorted(catalog.values(), key=lambda o: o.acquisition_date)
        total = len(all_obs)
        sliced = all_obs[offset : offset + limit]
        return sliced, total

    def get(self, id: str) -> Observation:
        catalog = self._load_catalog()
        if id not in catalog:
            raise KeyError(f"Observation '{id}' not found in mock catalog")
        return catalog[id]

    def open_asset(self, id: str) -> Path:
        obs = self.get(id)
        asset_rel = obs.asset_location
        asset_path = (self.catalog_dir / asset_rel).resolve()

        # Guard against path traversal
        try:
            asset_path.relative_to(self.catalog_dir)
        except ValueError:
            raise PermissionError(f"Access denied: Path traversal detected outside {self.catalog_dir}")

        if not asset_path.is_file():
            # Try fallback to {id}.tif
            fallback = (self.catalog_dir / f"{id}.tif").resolve()
            if fallback.is_file():
                return fallback
            raise FileNotFoundError(f"Asset file '{asset_rel}' not found for observation '{id}'")

        return asset_path
