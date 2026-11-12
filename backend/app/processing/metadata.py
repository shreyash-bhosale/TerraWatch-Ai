import json
from pathlib import Path
from typing import Any


class MetadataParsingError(Exception):
    """Raised when sidecar metadata is missing or invalid."""

def find_sidecar(raster_path: Path) -> Path | None:
    """
    Find sidecar JSON metadata corresponding to a raster file.
    Checks <name>.json in the same directory.
    """
    raster_path = Path(raster_path)
    sidecar = raster_path.with_suffix(".json")
    if sidecar.is_file():
        return sidecar
    return None

def normalize_metadata(data: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize raw sidecar metadata to conform to standard observation structure.
    """
    if not isinstance(data, dict):
        raise MetadataParsingError(f"Metadata must be a JSON dictionary, got {type(data).__name__}")

    # Ensure required ID and provider
    obs_id = str(data.get("id") or "")
    provider = str(data.get("provider") or "unknown")
    synthetic = bool(data.get("synthetic", False))
    acq_date = str(data.get("acquisition_date") or "")

    normalized = {
        "id": obs_id,
        "provider": provider,
        "synthetic": synthetic,
        "acquisition_date": acq_date,
        "geometry": data.get("geometry", {}),
        "asset_location": str(data.get("asset_location") or ""),
        "asset_format": str(data.get("asset_format") or "GTiff"),
        "product_name": data.get("product_name"),
        "polarization": data.get("polarization"),
        "frequency_band": data.get("frequency_band"),
        "orbit_direction": data.get("orbit_direction"),
        "processing_level": data.get("processing_level"),
        "measurement_units": data.get("measurement_units", "dB"),
        "resolution": float(data["resolution"]) if data.get("resolution") is not None else None,
        "crs": str(data["crs"]) if data.get("crs") is not None else None,
        "source_metadata": data.get("source_metadata", {}),
    }
    return normalized

def load_sidecar_metadata(sidecar_path: Path) -> dict[str, Any]:
    """
    Load and normalize metadata from a sidecar JSON file.
    """
    path = Path(sidecar_path)
    if not path.is_file():
        raise FileNotFoundError(f"Sidecar metadata file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        return normalize_metadata(raw_data)
    except json.JSONDecodeError as e:
        raise MetadataParsingError(f"Invalid JSON in sidecar {path}: {e!s}") from e
