"""
db/database.py
--------------
Manejo centralizado de la conexión a SQLite.
Todos los archivos que necesiten acceder a la BD importan desde aquí.
Nunca escribas rutas o conexiones directas en otros módulos.
"""

import sqlite3
import os
from config.settings  import DB_RUTA
from app.utils.logger import log


def obtener_conexion() -> sqlite3.Connection:
    """
    Retorna una conexión activa a la base de datos SQLite.
    Crea el archivo .db automáticamente si no existe.

    Uso estándar en cualquier controller o service:
        conn   = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute(...)
        conn.commit()   # solo si hubo INSERT / UPDATE / DELETE
        conn.close()

    Retorna:
        sqlite3.Connection con row_factory = sqlite3.Row
        (acceso por nombre de columna: fila["nombre"])
    """
    try:
        os.makedirs(os.path.dirname(DB_RUTA), exist_ok=True)

        conn = sqlite3.connect(DB_RUTA)

        # Permite acceder a columnas por nombre: fila["nombre_columna"]
        conn.row_factory = sqlite3.Row

        # Activa restricciones de clave foránea (desactivadas por defecto en SQLite)
        conn.execute("PRAGMA foreign_keys = ON")

        # Mejora rendimiento en escrituras múltiples
        conn.execute("PRAGMA journal_mode = WAL")

        return conn

    except sqlite3.Error as e:
        log.error(f"Error al conectar con la BD en '{DB_RUTA}': {e}")
        raise


def ejecutar_script_sql(sql: str):
    """
    Ejecuta un bloque SQL completo (CREATE TABLE, INSERT, etc.).
    Se usa principalmente en las migraciones.
    """
    try:
        conn = obtener_conexion()
        conn.executescript(sql)
        conn.commit()
        conn.close()
    except Exception as e:
        log.error(f"Error ejecutando script SQL: {e}")
        raise
