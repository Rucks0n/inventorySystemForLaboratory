"""
db/database.py
--------------
Manejo centralizado de la conexión a SQLite.
Todos los archivos que necesiten acceder a la BD importan desde aquí.
Nunca escribas rutas o conexiones directas en otros módulos.
"""

import sqlite3
import os
from contextlib import contextmanager
from config.settings  import DB_RUTA
from app.utils.logger import log


@contextmanager
def conexion():
    """
    Abre una conexión y la CIERRA SIEMPRE, aunque algo falle a mitad de camino.
    Es la forma de usar la base de datos en controllers y services:

        with conexion() as conn:
            conn.execute("UPDATE ...")
            conn.commit()      # solo si hubo INSERT / UPDATE / DELETE

    Si algo falla antes del commit, lo que quedó a medias se descarta.

    ¿Por qué importa? Una conexión que se queda abierta con una escritura a medias
    BLOQUEA la base: todo lo demás falla con «database is locked» hasta cerrar el programa.
    """
    conn = obtener_conexion()
    try:
        yield conn
    finally:
        conn.close()


def obtener_conexion() -> sqlite3.Connection:
    """
    Retorna una conexión activa a la base de datos SQLite.
    Crea el archivo .db automáticamente si no existe.

    Prefiere `with conexion() as conn:` (más arriba): cierra sola. Si usas esta función
    directamente, TÚ debes cerrar la conexión, también cuando hay un error (try/finally).

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
