"""Excepciones propias del conector Aruba ClearPass (NAC).

Separan los tres tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor y datos. Nunca exponemos excepciones
crípticas del cliente HTTP subyacente.
"""


class ClearPassConnectorError(Exception):
    """Error base del conector."""


class ClearPassAuthError(ClearPassConnectorError):
    """Credenciales inválidas o permisos insuficientes."""


class ClearPassNetworkError(ClearPassConnectorError):
    """No se pudo alcanzar el servicio (red, timeout o error del servidor)."""


class ClearPassDataError(ClearPassConnectorError):
    """La operación es válida pero los datos o parámetros no lo son."""
