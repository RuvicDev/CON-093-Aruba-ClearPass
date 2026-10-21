"""Prueba de conexión estándar del conector aruba_clearpass.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_ARUBA_CLEARPASS_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Obtiene un token OAuth2 y lista un endpoint de ClearPass con las env vars RUVIC_ARUBA_CLEARPASS_*."""
    try:
        from ruvic_aruba_clearpass_connector import (
            ClearPassAuthError,
            ClearPassClient,
            ClearPassDataError,
            ClearPassNetworkError,
        )
    except ImportError:
        return (
            False,
            (
                "La librería ruvic-aruba-clearpass-connector no está instalada. "
                "Instala con: pip install git+https://github.com/RuvicDev/"
                "CON-093-Aruba-ClearPass.git#subdirectory=lib"
            ),
        )

    try:
        client = ClearPassClient()  # valida que existan las env vars
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except ClearPassAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except ClearPassNetworkError as exc:
        return False, f"Error de red: {exc}"
    except ClearPassDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # noqa: BLE001 - red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return True, f"Conexión exitosa a ClearPass ({client.config.base_url})"


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
