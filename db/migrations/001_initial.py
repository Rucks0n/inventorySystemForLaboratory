"""
db/migrations/001_initial.py
-----------------------------
Primera migración del sistema.
Crea las tablas base: usuarios, productos, movimientos.

Para ejecutar manualmente:
    python db/migrations/001_initial.py
"""

import sys
import os

# Permite ejecutar este archivo directamente sin errores de importación
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from db.database import obtener_conexion
from app.utils.logger import log


def ejecutar():
    """Crea todas las tablas si no existen."""
    conn = obtener_conexion()
    cursor = conn.cursor()

    # ── Tabla de usuarios ──────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT    NOT NULL,
            usuario     TEXT    NOT NULL UNIQUE,
            contrasena  TEXT    NOT NULL,
            rol         TEXT    NOT NULL DEFAULT 'usuario',
            activo      INTEGER NOT NULL DEFAULT 1,
            creado_en   TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── Tabla de productos ─────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo      TEXT    NOT NULL UNIQUE,
            nombre      TEXT    NOT NULL,
            categoria   TEXT,
            cantidad    INTEGER NOT NULL DEFAULT 0,
            precio      REAL    NOT NULL DEFAULT 0.0,
            estado      TEXT    NOT NULL DEFAULT 'activo',
            creado_en   TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── Tabla de movimientos (entradas y salidas) ──────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id     INTEGER NOT NULL,
            tipo            TEXT    NOT NULL,   -- 'entrada' o 'salida'
            cantidad        INTEGER NOT NULL,
            observacion     TEXT,
            usuario_id      INTEGER,
            fecha           TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (producto_id) REFERENCES productos(id),
            FOREIGN KEY (usuario_id)  REFERENCES usuarios(id)
        )
    """)

    conn.commit()
    conn.close()
    log.info("Migración 001 ejecutada: tablas creadas correctamente.")
    print("✔ Tablas creadas correctamente.")


if __name__ == "__main__":
    ejecutar()