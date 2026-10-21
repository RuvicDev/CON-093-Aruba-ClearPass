# Conector Aruba ClearPass (NAC) (CON-093)

Conector Ruvic para Aruba ClearPass Policy Manager: endpoints, autorización y revocación de dispositivos, y sesiones activas.

## Instalación

```bash
pip install git+https://github.com/RuvicDev/CON-093-Aruba-ClearPass.git#subdirectory=lib
```

Python 3.10+. Dependencias: `requests>=2.31,<3.0`.

## Permisos requeridos

Autenticación **OAuth2 client_credentials** en `POST /api/oauth`.

1. En **ClearPass Guest → Administration → Operator Logins → Profiles**, crea un perfil de operador con: **API Services → Allow API Access**; **Policy Manager → Identity → Endpoints** (lectura y escritura); **Active Sessions** (lectura y desconexión). Nada más.
2. En **Administration → API Services → API Clients → Create API client**: grant type **Client credentials**, el perfil anterior. Copia el Client Secret (se muestra una sola vez).
3. Para que `revoke_access` bloquee el acceso, la política de Enforcement debe denegar `Endpoints Repository:Status EQUALS Disabled`.

## Variables de entorno (`RUVIC_ARUBA_CLEARPASS_*`)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_ARUBA_CLEARPASS_BASE_URL` | Sí | URL de ClearPass |
| `RUVIC_ARUBA_CLEARPASS_CLIENT_ID` | Sí | Client ID |
| `RUVIC_ARUBA_CLEARPASS_CLIENT_SECRET` | Sí | Client Secret |
| `RUVIC_ARUBA_CLEARPASS_VERIFY_SSL` | No (default `true`) | Verificar certificado SSL |
| `RUVIC_ARUBA_CLEARPASS_CONNECT_TIMEOUT` | No (default `15`) | Timeout de conexión (segundos) |

Los campos opcionales vacíos usan su valor por defecto (la plataforma envía
`""` cuando un campo queda en blanco).

## Pruebas locales

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_ARUBA_CLEARPASS_BASE_URL=...
export RUVIC_ARUBA_CLEARPASS_CLIENT_ID=...
export RUVIC_ARUBA_CLEARPASS_CLIENT_SECRET=...

python test_connection.py
python validate_local.py
```

`validate_local.py` lista endpoints y sesiones. Autorizar, revocar y desconectar están comentados: úsalos con una MAC de pruebas.

## Notas de integración

- Rutas verificadas contra pyclearpass, el SDK oficial de Aruba: `/api/oauth`, `/api/endpoint`, `/api/endpoint/mac-address/{mac}`, `/api/session`, `/api/session/{id}/disconnect`.
- `authorize_device` y `revoke_access` hacen `PATCH` del estado; si el endpoint no existe, lo crean con `POST`.
- `disconnect_session` exige `confirm_disconnect: true`; el conector nunca usa la acción masiva de desconexión (que con filtro vacío desconecta todas las sesiones).
- El token OAuth se cachea hasta 60 s antes de vencer.

## Limitaciones conocidas

- No crea ni edita políticas, roles ni perfiles de enforcement.
- No elimina endpoints.
- Los campos de `list_sessions` varían según la versión de ClearPass.
