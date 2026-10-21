"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_ARUBA_CLEARPASS_.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_ARUBA_CLEARPASS_"


def _env_int(name: str, default: int) -> int:
    """Lee un entero tratando el string vacío como ausente: la plataforma
    envía "" cuando un campo opcional queda en blanco."""
    raw = (os.environ.get(f"{ENV_PREFIX}{name}") or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(
            f"{ENV_PREFIX}{name} debe ser un número entero, no {raw!r}."
        ) from None
    if value <= 0:
        raise ValueError(f"{ENV_PREFIX}{name} debe ser mayor que 0, no {value}.")
    return value


def _env_bool(name: str, default: bool) -> bool:
    """Lee un booleano ("true"/"false"); vacío o ausente = default."""
    raw = (os.environ.get(f"{ENV_PREFIX}{name}") or "").strip().lower()
    if not raw:
        return default
    if raw in ("true", "1", "yes", "si", "sí"):
        return True
    if raw in ("false", "0", "no"):
        return False
    raise ValueError(f"{ENV_PREFIX}{name} debe ser true o false, no {raw!r}.")


@dataclass(frozen=True)
class ClearPassConfig:
    """Parámetros de conexión a la API REST de ClearPass Policy Manager (OAuth2 client_credentials)."""

    base_url: str
    client_id: str
    client_secret: str
    verify_ssl: bool = True
    connect_timeout: int = 15

    @classmethod
    def from_env(cls) -> ClearPassConfig:
        """Construye la configuración desde las variables RUVIC_ARUBA_CLEARPASS_*.

        Raises:
            ValueError: si falta alguna variable obligatoria o un valor no
                tiene el formato esperado.
        """
        missing = [
            f"{ENV_PREFIX}{name}"
            for name in ("BASE_URL", "CLIENT_ID", "CLIENT_SECRET",)
            if not (os.environ.get(f"{ENV_PREFIX}{name}") or "").strip()
        ]
        if missing:
            raise ValueError(
                "Faltan variables de entorno del conector aruba_clearpass: "
                + ", ".join(missing)
                + ". Configura el conector en Settings → Conectores."
            )
        return cls(
            base_url=os.environ[f"{ENV_PREFIX}BASE_URL"].rstrip("/"),
            client_id=os.environ[f"{ENV_PREFIX}CLIENT_ID"].strip(),
            client_secret=os.environ[f"{ENV_PREFIX}CLIENT_SECRET"],
            verify_ssl=_env_bool("VERIFY_SSL", True),
            connect_timeout=_env_int("CONNECT_TIMEOUT", 15),
        )
