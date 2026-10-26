"""
app/services/importador/perfiles.py
-----------------------------------
Perfiles de importación: el formato de columnas de un laboratorio, guardado
con un nombre (ver db/migrations/migration_003.py).

Un perfil es  nombre + mapeo  donde el mapeo es  {campo: encabezado normalizado}.
La búsqueda de cuál perfil encaja con un archivo está en mapeo.py.
"""

import json

from db.database      import obtener_conexion
from app.utils.logger import log


def listar() -> list[dict]:
    """Todos los perfiles guardados: [{"id", "nombre", "mapeo"}]."""
    conn = obtener_conexion()
    try:
        perfiles = []
        for f in conn.execute("SELECT id, nombre, mapeo FROM perfiles_importacion ORDER BY nombre"):
            try:
                perfiles.append({"id": f["id"], "nombre": f["nombre"], "mapeo": json.loads(f["mapeo"])})
            except ValueError:
                log.warning(f"Perfil de importación '{f['nombre']}' dañado; se ignora.")
        return perfiles
    finally:
        conn.close()


def guardar(nombre: str, mapeo: dict[str, str]) -> None:
    """Crea el perfil o, si ya existe uno con ese nombre (sin importar mayúsculas), lo reemplaza."""
    nombre = " ".join(str(nombre or "").split())
    if not nombre:
        raise ValueError("El perfil necesita un nombre.")
    if not mapeo:
        raise ValueError("No hay columnas asignadas para guardar.")
    conn = obtener_conexion()
    try:
        conn.execute("""
            INSERT INTO perfiles_importacion (nombre, mapeo) VALUES (?, ?)
            ON CONFLICT(nombre) DO UPDATE SET mapeo = excluded.mapeo
        """, (nombre, json.dumps(mapeo, ensure_ascii=False)))
        conn.commit()
        log.info(f"Perfil de importación guardado: '{nombre}'")
    finally:
        conn.close()
