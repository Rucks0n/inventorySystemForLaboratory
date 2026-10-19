"""
db/migrations/migration_001.py
------------------------------
Migración base del sistema.
Crea todas las tablas. Los depósitos ya NO vienen hardcodeados —
el administrador los crea desde la interfaz.

Para ejecutar manualmente desde la raíz:
    python db/migrations/migration_001.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))))

from db.database      import obtener_conexion
from app.utils.logger import log


def ejecutar():
    conn   = obtener_conexion()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS depositos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT    NOT NULL UNIQUE,
            descripcion TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            deposito_id     INTEGER NOT NULL,
            nombre          TEXT    NOT NULL,
            referencia      TEXT,
            cantidad_total  INTEGER NOT NULL DEFAULT 0,
            cantidad_disp   INTEGER NOT NULL DEFAULT 0,
            cantidad_prest  INTEGER NOT NULL DEFAULT 0,
            veces_prestado  INTEGER NOT NULL DEFAULT 0,
            ubicacion       TEXT,
            observaciones   TEXT,
            FOREIGN KEY (deposito_id) REFERENCES depositos(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS docentes (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre  TEXT    NOT NULL,
            correo  TEXT    NOT NULL UNIQUE,
            motivo  TEXT,
            activo  INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT    NOT NULL,
            codigo      TEXT    NOT NULL UNIQUE,
            correo      TEXT,
            telefono    TEXT,
            contrasena  TEXT,
            rol         TEXT    NOT NULL DEFAULT 'usuario',
            activo      INTEGER NOT NULL DEFAULT 1,
            creado_en   TEXT    DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prestamos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id          INTEGER NOT NULL,
            usuario_id       INTEGER NOT NULL,
            docente_id       INTEGER,
            cantidad         INTEGER NOT NULL DEFAULT 1,
            motivo           TEXT,
            fecha_prestamo   TEXT    DEFAULT (datetime('now')),
            fecha_limite     TEXT,
            fecha_devolucion TEXT,
            estado           TEXT    NOT NULL DEFAULT 'activo',
            observaciones    TEXT,
            FOREIGN KEY (item_id)    REFERENCES items(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (docente_id) REFERENCES docentes(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devoluciones (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            prestamo_id   INTEGER NOT NULL,
            item_id       INTEGER NOT NULL,
            usuario_id    INTEGER NOT NULL,
            cantidad      INTEGER NOT NULL DEFAULT 1,
            fecha         TEXT    DEFAULT (datetime('now')),
            observaciones TEXT,
            FOREIGN KEY (prestamo_id) REFERENCES prestamos(id),
            FOREIGN KEY (item_id)     REFERENCES items(id),
            FOREIGN KEY (usuario_id)  REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id       INTEGER,
            usuario_id    INTEGER,
            docente_id    INTEGER,
            tipo          TEXT    NOT NULL,
            cantidad      INTEGER NOT NULL,
            motivo        TEXT,
            fecha         TEXT    DEFAULT (datetime('now')),
            observaciones TEXT,
            FOREIGN KEY (item_id)    REFERENCES items(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (docente_id) REFERENCES docentes(id)
        )
    """)

    conn.commit()
    conn.close()
    log.info("Migración 001 ejecutada: tablas creadas.")
    print("✔  Tablas creadas correctamente.")


if __name__ == "__main__":
    ejecutar()
