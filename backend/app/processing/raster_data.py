from dataclasses import dataclass
from typing import Tuple
import numpy as np
from rasterio.transform import Affine
from rasterio.crs import CRS

@dataclass
class RasterData:
    """
    Standard in-memory representation of 2D raster data for TerraWatch AI processing.
    """
    array: np.ndarray  # 2D float32 array
    transform: Affine
    crs: CRS
    nodata: float
    bounds: Tuple[float, float, float, float]  # (west, south, east, north)
    resolution: Tuple[float, float]  # (rx, ry)
    units: str = "dB"

    def __post_init__(self):
        if self.array.ndim != 2:
            raise ValueError(f"Raster array must be 2-dimensional (H, W), got shape {self.array.shape}")
        if self.array.dtype != np.float32:
            self.array = self.array.astype(np.float32)

    @property
    def shape(self) -> Tuple[int, int]:
        return self.array.shape

    @property
    def height(self) -> int:
        return self.array.shape[0]

    @property
    def width(self) -> int:
        return self.array.shape[1]
