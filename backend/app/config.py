import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    VERSION: str = "0.1.0"
    PROVIDER: str = "mock"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    DATA_DIR: str = "data"
    LOCAL_DATA_DIR: str = "data/local"
    MAX_AOI_AREA_KM2: float = 50000.0
    MAX_BODY_BYTES: int = 1_048_576
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def data_path(self) -> Path:
        return Path(self.DATA_DIR).resolve()

    @property
    def synthetic_data_path(self) -> Path:
        return self.data_path / "synthetic"

    @property
    def jobs_data_path(self) -> Path:
        return self.data_path / "jobs"

    @property
    def outputs_data_path(self) -> Path:
        return self.data_path / "outputs"

    @property
    def local_data_path(self) -> Path:
        return Path(self.LOCAL_DATA_DIR).resolve()

    def validate_provider(self) -> None:
        valid_providers = {"mock", "local", "nisar"}
        if self.PROVIDER not in valid_providers:
            raise ValueError(
                f"Unknown PROVIDER '{self.PROVIDER}'. Valid options are: {', '.join(sorted(valid_providers))}"
            )

settings = Settings()
settings.validate_provider()
