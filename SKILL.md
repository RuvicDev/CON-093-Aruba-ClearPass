---
name: aruba-clearpass
description: >
  Usa la librería ruvic_aruba_clearpass_connector para el control de
  acceso a la red con Aruba ClearPass - consultar endpoints (list_endpoints,
  get_endpoint), autorizar un dispositivo (authorize_device), revocar el
  acceso de un dispositivo (revoke_access), consultar sesiones activas
  (list_sessions) y desconectar una sesión (disconnect_session). Úsala
  cuando el usuario pida dar o quitar acceso a la red a un equipo, revisar
  qué dispositivos o usuarios están conectados, o expulsar una sesión.
triggers:
- clearpass
- nac
- control de acceso a la red
- bloquear dispositivo
- autorizar mac
- sesiones activas
- 802.1x
---

# Conector Aruba ClearPass (NAC) (ruvic_aruba_clearpass_connector)

Librería Python para la API REST de Aruba ClearPass Policy Manager. Está **preinstalada en el runtime** cuando el
conector está configurado (si no, instálala con
`pip install git+https://github.com/RuvicDev/CON-093-Aruba-ClearPass.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de
variables de entorno, disponibles cuando el conector `aruba_clearpass` está
configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_ARUBA_CLEARPASS_BASE_URL` | URL de ClearPass |
| `RUVIC_ARUBA_CLEARPASS_CLIENT_ID` | Client ID |
| `RUVIC_ARUBA_CLEARPASS_CLIENT_SECRET` | Client Secret |
| `RUVIC_ARUBA_CLEARPASS_VERIFY_SSL` | (opcional) Verificar certificado SSL, default true |
| `RUVIC_ARUBA_CLEARPASS_CONNECT_TIMEOUT` | (opcional) Timeout de conexión (segundos), default 15 |

Si estas variables NO existen, el conector no está configurado: no
generes código que lo use; indica al usuario que lo configure en
**Settings → Conectores**. El código generado **NUNCA** usa nombres con
segmento de alias (`_DEFAULT_INSTANCIA_`, `_PRODUCCION_`, etc.) salvo que
aparezcan en una sección autogenerada `## Variables en tu entorno` al final
de este skill.

## Autorizar, revocar y desconectar son acciones reales

`list_endpoints`, `get_endpoint` y `list_sessions` son de solo lectura.
`authorize_device` y `revoke_access` **cambian el estado real** del
endpoint (Known / Disabled) y aplican en su siguiente autenticación;
`disconnect_session` expulsa al dispositivo de la red de inmediato.
Ejecútalas solo cuando el usuario lo pida, confirma la MAC con
`get_endpoint` y registra el motivo en `reason`.

## Conexión (siempre igual)

```python
from ruvic_aruba_clearpass_connector import ClearPassClient

client = ClearPassClient()  # lee RUVIC_ARUBA_CLEARPASS_* del entorno automáticamente
```

## Capacidad 1 — Consultar endpoints

```python
deshabilitados = client.list_endpoints(status="Disabled", limit=20)
equipo = client.get_endpoint("12:34:56:78:90:ab")
print(equipo["status"], equipo["description"])
```

## Capacidad 2 — Autorizar un dispositivo

```python
client.authorize_device("12:34:56:78:90:ab", reason="Impresora piso 3, ticket 881")
```

Si el endpoint no existe, se crea con estado Known.

## Capacidad 3 — Revocar el acceso

```python
client.revoke_access("12:34:56:78:90:ab", reason="Equipo robado, INC-552")
```

Las políticas de ClearPass deben denegar los endpoints Disabled. Para expulsarlo ya, desconecta su sesión.

## Capacidad 4 — Sesiones activas y desconexión

```python
sesiones = client.list_sessions(username="ana.perez")
for s in sesiones:
    print(s["id"], s.get("mac_address"), s.get("framedipaddress"))
client.disconnect_session(sesiones[0]["id"])
```

## Manejo de errores

```python
from ruvic_aruba_clearpass_connector import (
    ClearPassAuthError, ClearPassDataError, ClearPassNetworkError,
)

try:
    client.revoke_access("12:34:56:78:90:ab", reason="INC-552")
except ClearPassAuthError as e:
    print(f"Credenciales o permisos: {e}")
except ClearPassNetworkError as e:
    print(f"No se pudo alcanzar el servicio: {e}")
except ClearPassDataError as e:
    print(f"Error de datos: {e}")
```

Muestra el mensaje de la excepción tal cual al usuario: indica qué corregir.

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_ARUBA_CLEARPASS_*` (el constructor de `ClearPassClient` ya lo hace).
2. Nunca imprimas `RUVIC_ARUBA_CLEARPASS_CLIENT_SECRET`.
3. Antes de revocar o desconectar, confirma con `get_endpoint` o `list_sessions` que la MAC o la sesión son las correctas.
4. Incluye siempre el motivo en `reason`: queda en la descripción del endpoint.
5. Revocar sin desconectar deja la sesión actual activa hasta la próxima autenticación: díselo al usuario.
