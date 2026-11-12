import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from shapely.geometry import shape

from app.providers.base import BaseProvider
from app.schemas.common import GeoJSONPolygonGeometry
from app.schemas.observation import Observation


def _parse_iso_date(date_str: str, is_end_of_day: bool = False) -> datetime:
    """Parse ISO date or date-time string into a UTC datetime object."""
    cleaned = date_str.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    if len(cleaned) == 10 and cleaned.count("-") == 2:
        if is_end_of_day:
            cleaned += "T23:59:59.999999+00:00"
        else:
            cleaned += "T00:00:00+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class LocalProvider(BaseProvider):
    """Local filesystem SAR provider scanning LOCAL_DATA_DIR for raster + sidecar JSON.
    
    Enforces strict path-traversal prevention and reports warnings for missing or malformed sidecars.
    """

    RASTER_EXTENSIONS = {".tif", ".tiff", ".geotiff", ".nc", ".h5", ".hdf5"}

    def __init__(self, local_dir: Path):
        self.local_dir = Path(local_dir).resolve()

    def _validate_path_contained(self, path: Path) -> Path:
        """Verify that resolved path stays strictly within the configured local_dir."""
        resolved = path.resolve()
        base = self.local_dir.resolve()
        try:
            resolved.relative_to(base)
        except ValueError:
            raise PermissionError("Access denied: Path traversal detected")
        return resolved

    def _scan(self, warnings: Optional[List[str]] = None) -> Dict[str, Observation]:
        catalog: Dict[str, Observation] = {}
        if not self.local_dir.is_dir():
            return catalog

        for file_path in sorted(self.local_dir.iterdir()):
            if file_path.suffix.lower() not in self.RASTER_EXTENSIONS:
                continue

            # Check for sidecar JSON
            sidecar_path = file_path.with_suffix(".json")
            if not sidecar_path.is_file():
                if warnings is not None:
                    warnings.append(
                        f"Raster '{file_path.name}' is missing required sidecar '{sidecar_path.name}', skipping."
                    )
                continue

            try:
                # Ensure sidecar path is inside local_dir
                self._validate_path_contained(sidecar_path)
                data = json.loads(sidecar_path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("Sidecar root must be a JSON object")
                if "id" not in data or "geometry" not in data:
                    raise ValueError("Sidecar missing required 'id' or 'geometry' fields")

                obs = Observation.model_validate(data)
                # Verify that asset location is also contained within local_dir
                asset_full = self._validate_path_contained(self.local_dir / obs.asset_location)
                if not asset_full.is_file():
                    raise FileNotFoundError(f"Referenced asset '{obs.asset_location}' does not exist")

                catalog[obs.id] = obs
            except PermissionError:
                raise
            except Exception as e:
                if warnings is not None:
                    warnings.append(f"Invalid sidecar for raster '{file_path.name}': {e}, skipping.")
                continue

        return catalog

    def search(
        self,
        aoi: GeoJSONPolygonGeometry,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[List[Observation], List[str]]:
        warnings: List[str] = []
        catalog = self._scan(warnings=warnings)
        aoi_poly = shape(aoi.model_dump())

        start_dt = _parse_iso_date(start_date) if start_date else None
        end_dt = _parse_iso_date(end_date, is_end_of_day=True) if end_date else None

        matching: List[Observation] = []
        for obs in catalog.values():
            obs_dt = _parse_iso_date(obs.acquisition_date)
            if start_dt and obs_dt < start_dt:
                continue
            if end_dt and obs_dt > end_dt:
                continue

            obs_poly = shape(obs.geometry.model_dump())
            if aoi_poly.intersects(obs_poly) and not aoi_poly.intersection(obs_poly).is_empty:
                matching.append(obs)

        matching.sort(key=lambda o: o.acquisition_date)
        return matching, warnings

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Observation], int]:
        catalog = self._scan()
        all_obs = sorted(catalog.values(), key=lambda o: o.acquisition_date)
        total = len(all_obs)
        sliced = all_obs[offset : offset + limit]
        return sliced, total

    def get(self, id: str) -> Observation:
        # Prevent traversal in ID
        if ".." in id or "/" in id or "\\" in id:
            raise PermissionError("Access denied: Invalid observation ID")

        catalog = self._scan()
        if id not in catalog:
            raise KeyError(f"Observation '{id}' not found in local provider")
        return catalog[id]

    def open_asset(self, id: str) -> Path:
        obs = self.get(id)
        asset_full = self._validate_path_contained(self.local_dir / obs.asset_location)
        if not asset_full.is_file():
            raise FileNotFoundError(f"Asset file '{obs.asset_location}' not found for observation '{id}'")
        return asset_full
