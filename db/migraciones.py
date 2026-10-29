"""
db/migraciones.py
-----------------
Control de versiones de la base de datos.

Cada cambio en la estructura de la BD vive en su propio archivo
(db/migrations/migration_00X.py) y se aplica UNA sola vez, en orden.
La tabla `migraciones_aplicadas` guarda cuáles ya se aplicaron.

CÓMO AGREGAR UN CAMBIO NUEVO A LA BASE
    1. Crea db/migrations/migration_00X.py con una función ejecutar().
       Debe poder repetirse sin dañar nada (usa CREATE ... IF NOT EXISTS
       y revisa si una columna ya existe antes de agregarla).
    2. Agrégala al final de la lista MIGRACIONES de este archivo.
    Listo: se aplicará sola la próxima vez que se abra la app.

Si la base ya tiene datos, antes de aplicar cambios se guarda una copia
de seguridad en db/respaldos/.
"""

from db.database          import obtener_conexion
from db.respaldos         import crear_respaldo
from db.migrations        import migration_001, migration_002, migration_003, migration_004
from app.utils.logger     import log

# (número, descripción, función que aplica el cambio)
# El número no se repite ni se reutiliza. Se agregan siempre al final.
MIGRACIONES = [
    (1, "Tablas base del sistema",     migration_001.ejecutar),
    (2, "Tipos de ítem y unidad",      migration_002.ejecutar),
    (3, "Perfiles de importación",     migration_003.ejecutar),
    (4, "Historial conserva ítems eliminados", migration_004.ejecutar),
]


def _versiones_aplicadas() -> set[int]:
    """Lee qué migraciones ya se aplicaron (crea la tabla de control si falta)."""
    conn = obtener_conexion()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS migraciones_aplicadas (
                version     INTEGER PRIMARY KEY,
                descripcion TEXT    NOT NULL,
                aplicada_en TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        return {f["version"] for f in conn.execute("SELECT version FROM migraciones_aplicadas")}
    finally:
        conn.close()


def _base_con_datos() -> bool:
    """True si la BD ya tenía la tabla de ítems antes de migrar (instalación existente)."""
    conn = obtener_conexion()
    try:
        fila = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='items'"
        ).fetchone()
        return fila is not None
    finally:
        conn.close()


def _registrar(version: int, descripcion: str):
    conn = obtener_conexion()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO migraciones_aplicadas (version, descripcion) VALUES (?, ?)",
            (version, descripcion),
        )
        conn.commit()
    finally:
        conn.close()


def aplicar_pendientes() -> list[str]:
    """
    Aplica, en orden, las migraciones que todavía no se han aplicado.
    Es seguro llamarla en cada arranque: si no hay nada pendiente, no hace nada.

    Retorna la lista de mensajes de lo que se aplicó (vacía si no había nada).
    """
    ya_aplicadas = _versiones_aplicadas()
    pendientes   = [m for m in MIGRACIONES if m[0] not in ya_aplicadas]
    if not pendientes:
        return []

    if _base_con_datos():
        crear_respaldo("antes_de_migrar")

    mensajes = []
    for version, descripcion, aplicar in pendientes:
        aplicar()
        _registrar(version, descripcion)
        mensajes.append(f"Migración {version:03d} aplicada: {descripcion}")
        log.info(mensajes[-1])
    return mensajes
