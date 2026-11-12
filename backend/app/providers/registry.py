from app.config import settings
from app.providers.base import BaseProvider
from app.providers.local_provider import LocalProvider
from app.providers.mock_provider import MockProvider


def get_provider() -> BaseProvider:
    """Retrieve the configured SAR data provider according to settings.PROVIDER.

    Returns:
        An instance of BaseProvider.

    Raises:
        NotImplementedError: If settings.PROVIDER == "nisar".
        ValueError: If settings.PROVIDER is not recognized.
    """
    provider_name = settings.PROVIDER.lower().strip()

    if provider_name == "mock":
        return MockProvider(settings.synthetic_data_path)
    elif provider_name == "local":
        return LocalProvider(settings.local_data_path)
    elif provider_name == "nisar":
        raise NotImplementedError("BLOCKED: awaiting official NISAR resources")
    else:
        raise ValueError(f"Unknown PROVIDER '{settings.PROVIDER}'")
