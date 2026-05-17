"""
db/migrations/001_initial.py
-----------------------------
Primera y principal migración del sistema.
Crea todas las tablas basadas en la estructura real de los Excel originales:

    inventario.xlsx  →  depósitos (Depósito1/2/3) + docentes
    gestion.xlsx     →  préstamos, devoluciones, movimientos

Tablas creadas:
    depositos     — los 3 depósitos físicos donde se almacenan los ítems
    items         — cada ítem de inventario con su stock y disponibilidad
    docentes      — docentes que pueden solicitar préstamos
    usuarios      — usuarios del sistema (estudiantes / personal)
    prestamos     — préstamos activos e históricos
    devoluciones  — registro de cada devolución
    movimientos   — historial completo (Salida / Devolución / Entrada)

Para ejecutar manualmente desde la raíz del proyecto:
    python db/migrations/001_initial.py
"""

import sys
import os

# Permite ejecutar este archivo directamente sin errores de importación
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))))

from db.database      import obtener_conexion
from app.utils.logger import log


def ejecutar():
    """Crea todas las tablas si aún no existen. Seguro de ejecutar más de una vez."""

    conn   = obtener_conexion()
    cursor = conn.cursor()

    # ── depositos ──────────────────────────────────────────────────────────────
    # Cada hoja del inventario.xlsx representa un depósito físico
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS depositos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT    NOT NULL UNIQUE,
            descripcion TEXT
        )
    """)

    # ── items ──────────────────────────────────────────────────────────────────
    # Columnas originales: ID Item | Item | Referencia | Cantidad | Ubicación | Observaciones
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

    # ── docentes ───────────────────────────────────────────────────────────────
    # Hoja 'Docente' de inventario.xlsx: Docente | Correo | Motivo
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS docentes (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre  TEXT    NOT NULL,
            correo  TEXT    NOT NULL UNIQUE,
            motivo  TEXT,
            activo  INTEGER NOT NULL DEFAULT 1
        )
    """)

    # ── usuarios ───────────────────────────────────────────────────────────────
    # Estudiantes o personal que solicitan préstamos y acceden al sistema
    # Los usuarios del sistema llevan contraseña; los solicitantes de préstamos no
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT    NOT NULL,
            codigo      TEXT    NOT NULL UNIQUE,
            correo      TEXT,
            telefono    TEXT,
            contrasena  TEXT,                          -- NULL si es solo solicitante
            rol         TEXT    NOT NULL DEFAULT 'usuario',
            activo      INTEGER NOT NULL DEFAULT 1,
            creado_en   TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── prestamos ──────────────────────────────────────────────────────────────
    # Hoja 'Prestamos' de gestion.xlsx
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

    # ── devoluciones ───────────────────────────────────────────────────────────
    # Hoja 'Devoluciones' de gestion.xlsx
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

    # ── movimientos ────────────────────────────────────────────────────────────
    # Hoja 'Movimientos' de gestion.xlsx: historial completo
    # Tipo: 'Salida' | 'Devolución' | 'Entrada'
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

    # ── Datos iniciales: los 3 depósitos del sistema original ─────────────────
    cursor.executemany("""
        INSERT OR IGNORE INTO depositos (nombre, descripcion) VALUES (?, ?)
    """, [
        ("Depósito1", "Materiales de impresión 3D y filamentos"),
        ("Depósito2", "Componentes neumáticos y electromecánicos"),
        ("Depósito3", "Equipos de soldadura y kits electrónicos"),
    ])

    conn.commit()
    conn.close()

    log.info("Migración 001 ejecutada: todas las tablas creadas correctamente.")
    print("✔  Tablas creadas correctamente.")


if __name__ == "__main__":
    ejecutar()
