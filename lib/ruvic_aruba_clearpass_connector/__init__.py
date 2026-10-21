"""Control de acceso a la red con Aruba ClearPass: consultar endpoints, autorizar dispositivos, revocar acceso y consultar o desconectar sesiones"""

from .client import ClearPassClient
from .config import ENV_PREFIX, ClearPassConfig
from .exceptions import (
    ClearPassAuthError,
    ClearPassConnectorError,
    ClearPassDataError,
    ClearPassNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ClearPassAuthError",
    "ClearPassClient",
    "ClearPassConfig",
    "ClearPassConnectorError",
    "ClearPassDataError",
    "ClearPassNetworkError",
    "ENV_PREFIX",
    "setup_logging",
]

__version__ = "1.0.0"
