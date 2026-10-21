"""Cliente de control de acceso a la red para Aruba ClearPass Policy Manager (API REST).

Capacidades:
- list_endpoints():      consultar endpoints (dispositivos) registrados.
- get_endpoint():        consultar un endpoint por su MAC.
- authorize_device():    autorizar un dispositivo (estado "Known").
- revoke_access():       revocar el acceso de un dispositivo (estado "Disabled").
- list_sessions():       consultar sesiones activas.
- disconnect_session():  desconectar una sesión activa.

Autenticación: OAuth2 client_credentials en POST /api/oauth.

Las credenciales SIEMPRE provienen de variables de entorno RUVIC_ARUBA_CLEARPASS_*
(ver config.ClearPassConfig.from_env). Prohibido hardcodearlas.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.parse import quote

import requests
import urllib3

from .config import ClearPassConfig
from .exceptions import ClearPassAuthError, ClearPassDataError, ClearPassNetworkError
from .logging_utils import get_logger

_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}[:-]?){5}[0-9A-Fa-f]{2}$")
_STATUSES = {"Known", "Unknown", "Disabled"}


def _mac(value: Any) -> str:
    if not isinstance(value, str) or not _MAC_RE.match(value.strip()):
        raise ClearPassDataError(f"mac inválida: {value!r}. Formato esperado 12:34:56:78:90:ab.")
    raw = re.sub(r"[^0-9a-fA-F]", "", value).lower()
    return ":".join(raw[i:i + 2] for i in range(0, 12, 2))


def _limit(value: Any, maximum: int = 1000) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ClearPassDataError(f"limit debe ser un entero entre 1 y {maximum}.")
    return value


def _endpoint(e: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": e.get("id"),
        "mac": e.get("mac_address"),
        "status": e.get("status"),
        "description": e.get("description"),
        "device_category": (e.get("profile") or {}).get("device_category") if isinstance(e.get("profile"), dict) else None,
        "attributes": e.get("attributes"),
        "updated_at": e.get("updated_at"),
    }


class ClearPassClient:
    """Cliente de ClearPass Policy Manager.

    Args:
        config: configuración. Si se omite, se lee de RUVIC_ARUBA_CLEARPASS_*.

    Ejemplo:
        >>> client = ClearPassClient()
        >>> client.get_endpoint("12:34:56:78:90:ab")
        {'id': 3021, 'mac': '123456789...', 'status': 'Known', ...}
    """

    def __init__(self, config: ClearPassConfig | None = None) -> None:
        self.config = config or ClearPassConfig.from_env()
        self.api_url = f"{self.config.base_url.removesuffix('/api')}/api"
        self._logger = get_logger()
        self._session = requests.Session()
        self._session.verify = self.config.verify_ssl
        self._token: str | None = None
        self._token_expiry = 0.0
        if not self.config.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        try:
            resp = self._session.post(f"{self.api_url}/oauth", json={
                "grant_type": "client_credentials",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
            }, timeout=self.config.connect_timeout)
        except requests.exceptions.SSLError as exc:
            raise ClearPassNetworkError(
                "Error de certificado SSL. Si ClearPass usa un certificado autofirmado, desactiva "
                "'Verificar certificado SSL' en la configuración del conector."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ClearPassNetworkError(f"No se pudo alcanzar ClearPass ({self.config.base_url}): {exc}") from exc
        if resp.status_code in (400, 401, 403):
            raise ClearPassAuthError(
                "Client ID o Client Secret inválidos, o el API Client no tiene el grant type "
                "'Client credentials' habilitado."
            )
        if resp.status_code >= 400:
            raise ClearPassNetworkError(f"ClearPass respondió {resp.status_code} al pedir el token.")
        body = resp.json()
        self._token = body["access_token"]
        self._token_expiry = time.time() + int(body.get("expires_in", 3600))
        return self._token

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = {"Authorization": f"Bearer {self._get_token()}", "Accept": "application/json"}
        try:
            resp = self._session.request(method, f"{self.api_url}{path}", headers=headers,
                                         timeout=self.config.connect_timeout, **kwargs)
        except requests.exceptions.RequestException as exc:
            raise ClearPassNetworkError(f"Error de red con ClearPass: {exc}") from exc
        if resp.status_code == 401:
            raise ClearPassAuthError("ClearPass rechazó el token; revisa el API Client.")
        if resp.status_code == 403:
            raise ClearPassAuthError(
                "El perfil de operador del API Client no tiene permiso para esta operación "
                "(Endpoints o Active Sessions)."
            )
        if resp.status_code == 404:
            raise ClearPassDataError("El endpoint o la sesión no existe en ClearPass.")
        if resp.status_code == 422:
            raise ClearPassDataError(f"ClearPass rechazó los datos: {resp.text[:300]}")
        if resp.status_code >= 500:
            raise ClearPassNetworkError(f"ClearPass respondió {resp.status_code}; reintenta en unos segundos.")
        if resp.status_code >= 400:
            raise ClearPassDataError(f"ClearPass respondió {resp.status_code}: {resp.text[:300]}")
        return resp.json() if resp.content else None

    def ping(self) -> bool:
        """Verifica credenciales y permisos listando un endpoint.

        Raises:
            ClearPassAuthError / ClearPassNetworkError / ClearPassDataError.
        """
        self._request("GET", "/endpoint", params={"limit": 1})
        self._logger.info("Ping exitoso a ClearPass %s", self.config.base_url)
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: endpoints
    # ------------------------------------------------------------------ #

    def list_endpoints(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Lista endpoints registrados.

        Args:
            status: "Known", "Unknown" o "Disabled" (opcional).
            limit: máximo de endpoints (1-1000).

        Returns:
            Lista de dicts: id, mac, status, description, device_category,
            attributes, updated_at.

        Ejemplo:
            >>> client.list_endpoints(status="Disabled")
            [{'id': 3021, 'mac': '1234567890ab', 'status': 'Disabled', ...}]
        """
        params: dict[str, Any] = {"limit": _limit(limit), "sort": "-id"}
        if status:
            if status.capitalize() not in _STATUSES:
                raise ClearPassDataError(f"status {status!r} inválido. Valores permitidos: {sorted(_STATUSES)}")
            params["filter"] = json.dumps({"status": status.capitalize()})
        data = self._request("GET", "/endpoint", params=params) or {}
        items = (data.get("_embedded") or {}).get("items", [])
        self._logger.info("Endpoints listados: %d", len(items))
        return [_endpoint(e) for e in items]

    def get_endpoint(self, mac: str) -> dict[str, Any]:
        """Consulta un endpoint por su MAC.

        Ejemplo:
            >>> client.get_endpoint("12:34:56:78:90:ab")
            {'id': 3021, 'mac': '1234567890ab', 'status': 'Known', ...}
        """
        mac = _mac(mac)
        return _endpoint(self._request("GET", f"/endpoint/mac-address/{quote(mac, safe='')}") or {})

    # ------------------------------------------------------------------ #
    # Capacidad 2 y 3: autorizar / revocar
    # ------------------------------------------------------------------ #

    def _set_status(self, mac: str, status: str, reason: str | None) -> dict[str, Any]:
        mac = _mac(mac)
        body: dict[str, Any] = {"status": status}
        if reason:
            body["description"] = str(reason)[:250]
        try:
            result = self._request("PATCH", f"/endpoint/mac-address/{quote(mac, safe='')}", json=body)
        except ClearPassDataError as exc:
            if "no existe" not in str(exc):
                raise
            # El endpoint aún no está registrado: se crea con el estado pedido
            result = self._request("POST", "/endpoint", json={"mac_address": mac, **body})
        self._logger.info("Endpoint %s → %s", mac, status)
        return _endpoint(result or {})

    def authorize_device(self, mac: str, reason: str | None = None) -> dict[str, Any]:
        """Autoriza un dispositivo: lo deja en estado "Known" (lo crea si no existe).

        El cambio aplica en su siguiente autenticación; para forzarla,
        desconecta su sesión con disconnect_session().

        Ejemplo:
            >>> client.authorize_device("12:34:56:78:90:ab", reason="Impresora piso 3, ticket 881")
            {'id': 3021, 'status': 'Known', ...}
        """
        return self._set_status(mac, "Known", reason)

    def revoke_access(self, mac: str, reason: str | None = None) -> dict[str, Any]:
        """Revoca el acceso de un dispositivo: lo deja en estado "Disabled".

        Las políticas de ClearPass deben denegar los endpoints "Disabled"
        (regla sobre Endpoints Repository:Status). El cambio aplica en la
        siguiente autenticación; para expulsarlo ya, desconecta su sesión.

        Ejemplo:
            >>> client.revoke_access("12:34:56:78:90:ab", reason="Equipo robado, INC-552")
            {'id': 3021, 'status': 'Disabled', ...}
        """
        return self._set_status(mac, "Disabled", reason)

    # ------------------------------------------------------------------ #
    # Capacidad 4: sesiones
    # ------------------------------------------------------------------ #

    def list_sessions(self, username: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Consulta sesiones activas, de la más reciente a la más antigua.

        Args:
            username: filtra por nombre de usuario (opcional).
            limit: máximo de sesiones (1-1000).

        Returns:
            Lista de dicts con id y los campos de la sesión que entrega ClearPass
            (usuario, MAC, IP, NAS, hora de inicio, etc.).

        Ejemplo:
            >>> client.list_sessions(username="ana.perez")
            [{'id': 'R0000...', 'username': 'ana.perez', 'mac_address': '...', ...}]
        """
        params: dict[str, Any] = {"limit": _limit(limit), "sort": "-id"}
        if username:
            params["filter"] = json.dumps({"username": str(username)})
        data = self._request("GET", "/session", params=params) or {}
        items = (data.get("_embedded") or {}).get("items", [])
        self._logger.info("Sesiones activas listadas: %d", len(items))
        return [{k: v for k, v in s.items() if k != "_links"} for s in items]

    def disconnect_session(self, session_id: str) -> dict[str, Any]:
        """Desconecta una sesión activa (envía un Disconnect-Request al NAS).

        Args:
            session_id: ID de la sesión (campo 'id' de list_sessions).

        Ejemplo:
            >>> client.disconnect_session("R00001a2b-01-6a1b2c3d")
            {'session_id': 'R00001a2b-01-6a1b2c3d', 'result': {...}}
        """
        if not isinstance(session_id, str) or not session_id.strip():
            raise ClearPassDataError("session_id es obligatorio (obténlo con list_sessions).")
        sid = session_id.strip()
        result = self._request("POST", f"/session/{quote(sid, safe='')}/disconnect",
                               json={"id": sid, "confirm_disconnect": True})
        self._logger.info("Sesión %s desconectada", sid)
        return {"session_id": sid, "result": result}
