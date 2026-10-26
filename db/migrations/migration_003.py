"""
db/migrations/migration_003.py
------------------------------
Perfiles de importación.

Un perfil guarda cómo están organizadas las columnas del Excel de un laboratorio
(por ejemplo: "Laboratorio de Física usa Item, Cant. y Código"). Así, la
próxima vez que se suba un archivo con esas columnas, el sistema las asigna solo.

Es repetible y atómica (si algo falla, no queda nada a medias).
"""

from db.database      import obtener_conexion
from app.utils.logger import log


def ejecutar():
    conn = obtener_conexion()
    try:
        conn.execute("BEGIN")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS perfiles_importacion (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre    TEXT NOT NULL UNIQUE COLLATE NOCASE,
                mapeo     TEXT NOT NULL,                       -- JSON: {"campo": "encabezado"}
                creado_en TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        log.info("Migración 003 ejecutada: perfiles de importación.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
