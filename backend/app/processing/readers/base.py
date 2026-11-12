from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from rasterio.windows import Window
from app.processing.raster_data import RasterData

class BaseReader(ABC):
    """
    Abstract reader interface for geospatial rasters.
    """

    @abstractmethod
    def read(self, path: Path, window: Optional[Window] = None) -> RasterData:
        """
        Read a raster from disk, optionally within a bounding window.

        Args:
            path: Path to the raster file.
            window: Optional rasterio Window defining the subset to read.

        Returns:
            RasterData containing the extracted 2D float32 array and spatial metadata.
        """
        pass
