"""NISAR Provider Stub.

This provider is intentionally a non-functional stub.
Per Rule R2 and Section 7 of PRD.md:
Never invent NISAR endpoints, URLs, HDF5 paths, product names, polarizations,
auth flows, calibration steps or coverage. `nisar_provider.py` is a documented stub
that raises NotImplementedError("BLOCKED: awaiting official NISAR resources") and
is never registered as an active provider.

See docs/nisar-integration-checklist.md for the official integration checklist
once NISAR public data and APIs are officially released.
"""
from pathlib import Path
from typing import List, Optional, Tuple

from app.providers.base import BaseProvider
from app.schemas.common import GeoJSONPolygonGeometry
from app.schemas.observation import Observation


class NisarProvider(BaseProvider):
    """Documented stub provider for NISAR observations. Always raises NotImplementedError."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError("BLOCKED: awaiting official NISAR resources")

    def search(
        self,
        aoi: GeoJSONPolygonGeometry,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[List[Observation], List[str]]:
        raise NotImplementedError("BLOCKED: awaiting official NISAR resources")

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Observation], int]:
        raise NotImplementedError("BLOCKED: awaiting official NISAR resources")

    def get(self, id: str) -> Observation:
        raise NotImplementedError("BLOCKED: awaiting official NISAR resources")

    def open_asset(self, id: str) -> Path:
        raise NotImplementedError("BLOCKED: awaiting official NISAR resources")
