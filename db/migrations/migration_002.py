"""
db/migrations/migration_002.py
------------------------------
Tipos de ítem y unidad.

Qué hace:
    1. Crea la tabla `tipos_item` y la llena con dos tipos iniciales
       (el administrador puede agregar o editar más desde la app).
    2. Agrega a `items` las columnas `tipo_id` y `unidad`.
    3. Los ítems que ya existían quedan como "Herramienta", porque hasta
       ahora todos se podían prestar.

Cada tipo tiene un COMPORTAMIENTO:
    presta   → se presta y se devuelve (sensores, micrómetros, pesas)
    consume  → se gasta y se descuenta (aceites, reactivos, grafito)

Es repetible: lo que ya existe se salta. Todo ocurre en una sola
transacción, así que si algo falla no queda nada a medias.

NOTA: el código y la descripción del ítem NO se agregan aquí porque ya
existen como `referencia` y `observaciones`.
"""

from db.database      import obtener_conexion
from app.utils.logger import log

# Tipos con los que arranca la base: (nombre, comportamiento, descripción)
TIPOS_INICIALES = [
    ("Herramienta", "presta",  "Se presta y se devuelve (sensores, micrómetros, pesas)."),
    ("Consumible",  "consume", "Se gasta y se descuenta (aceites, reactivos, grafito)."),
]


def ejecutar():
    conn = obtener_conexion()
    try:
        conn.execute("BEGIN")

        # ── tipos_item ─────────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tipos_item (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                comportamiento TEXT    NOT NULL CHECK (comportamiento IN ('presta', 'consume')),
                descripcion    TEXT,
                activo         INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
            )
        """)
        if conn.execute("SELECT COUNT(*) FROM tipos_item").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO tipos_item (nombre, comportamiento, descripcion) VALUES (?, ?, ?)",
                TIPOS_INICIALES,
            )

        # ── columnas nuevas en items ───────────────────────────────────────
        columnas = {fila["name"] for fila in conn.execute("PRAGMA table_info(items)")}
        if "tipo_id" not in columnas:
            conn.execute("ALTER TABLE items ADD COLUMN tipo_id INTEGER REFERENCES tipos_item(id)")
        if "unidad" not in columnas:
            conn.execute("ALTER TABLE items ADD COLUMN unidad TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_tipo ON items(tipo_id)")

        # ── los ítems existentes eran todos prestables ─────────────────────
        conn.execute("""
            UPDATE items
            SET    tipo_id = (SELECT id FROM tipos_item WHERE nombre = 'Herramienta')
            WHERE  tipo_id IS NULL
        """)

        conn.commit()
        log.info("Migración 002 ejecutada: tipos de ítem y unidad.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
