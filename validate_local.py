"""Validación local del conector aruba_clearpass (solo lectura por defecto).

Uso:
    python validate_local.py

Requiere RUVIC_ARUBA_CLEARPASS_BASE_URL, RUVIC_ARUBA_CLEARPASS_CLIENT_ID y
RUVIC_ARUBA_CLEARPASS_CLIENT_SECRET exportadas.
"""

from ruvic_aruba_clearpass_connector import ClearPassClient, setup_logging

setup_logging("INFO")
client = ClearPassClient()

print("== 0. Ping ==")
client.ping()

print("== 1. Endpoints ==")
for e in client.list_endpoints(limit=5):
    print(f"  {e['mac']} {e['status']}")

print("== 2. Sesiones activas ==")
for s in client.list_sessions(limit=5):
    print(f"  {s.get('id')} {s.get('username')}")

# == 3. Acciones (ESCRIBEN): solo con una MAC de PRUEBAS ==
# MAC_PRUEBA = "02:00:00:00:00:01"
# print(client.authorize_device(MAC_PRUEBA, reason="Prueba Ruvic QA"))
# print(client.revoke_access(MAC_PRUEBA, reason="Fin prueba Ruvic QA"))

print("\nTodo OK.")
