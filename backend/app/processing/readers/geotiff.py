from pathlib import Path
from typing import Optional
import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.errors import RasterioIOError
from app.processing.readers.base import BaseReader
from app.processing.raster_data import RasterData

class CorruptRasterError(Exception):
    """Raised when a raster file cannot be opened, is corrupted, or has invalid structure."""
    pass

class GeoTIFFReader(BaseReader):
    """
    Reader for GeoTIFF raster files using rasterio.
    """

    def read(self, path: Path, window: Optional[Window] = None) -> RasterData:
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"Raster file not found: {path}")

        try:
            with rasterio.open(path) as src:
                if window is not None:
                    arr = src.read(1, window=window)
                    transform = rasterio.windows.transform(window, src.transform)
                    w, s, e, n = rasterio.windows.bounds(window, src.transform)
                    bounds = (float(w), float(s), float(e), float(n))
                else:
                    arr = src.read(1)
                    transform = src.transform
                    bounds = (float(src.bounds.left), float(src.bounds.bottom), float(src.bounds.right), float(src.bounds.top))

                crs = src.crs
                nodata = float(src.nodata) if src.nodata is not None else -9999.0
                res_x = float(abs(transform.a))
                res_y = float(abs(transform.e))
                units = src.tags().get("UNITS", "dB")

                return RasterData(
                    array=arr.astype(np.float32),
                    transform=transform,
                    crs=crs,
                    nodata=nodata,
                    bounds=bounds,
                    resolution=(res_x, res_y),
                    units=units,
                )
        except (RasterioIOError, Exception) as e:
            if isinstance(e, FileNotFoundError):
                raise
            raise CorruptRasterError(f"Corrupt or unreadable raster at {path}: {str(e)}") from e
