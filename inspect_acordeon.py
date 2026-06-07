import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection
cur = connection.cursor()

print("=== tarjetas_acordeonpage con titulo_padre vacío (15 registros) ===")
cur.execute(
    "SELECT id, legacy_id, titulo_padre, titulo_anexo "
    "FROM tarjetas_acordeonpage "
    "WHERE titulo_padre IS NULL OR titulo_padre = ''"
)
for row in cur.fetchall():
    print(" ", row)

print()
print("=== tarjetas_acordeonitem con contenido vacío (4 registros) ===")
cur.execute(
    "SELECT id, legacy_id, titulo, contenido "
    "FROM tarjetas_acordeonitem "
    "WHERE contenido IS NULL OR contenido = ''"
)
for row in cur.fetchall():
    print(" ", row)
