"""
Manejo de la conexión a SQLite.
Todos los archivos que necesiten acceder a la BD importan desde aquí.
Nunca escribas rutas o conexiones directas en otros archivos.
"""

import sqlite3
import os
from config.settings import DB_RUTA
from app.utils.logger import log


def obtener_conexion():
    """
    Retorna una conexión activa a la base de datos SQLite.
    Crea el archivo .db automáticamente si no existe.

    Uso:
        conn = obtener_conexion()
        cursor = conn.cursor()
        ...
        conn.close()
    """
    try:
        # Asegura que la carpeta db/ exista
        os.makedirs(os.path.dirname(DB_RUTA), exist_ok=True)

        conn = sqlite3.connect(DB_RUTA)

        # Retorna filas como diccionarios en vez de tuplas simples
        # Así puedes acceder a los datos por nombre: fila["nombre_producto"]
        conn.row_factory = sqlite3.Row

        # Activa claves foráneas (no están activas por defecto en SQLite)
        conn.execute("PRAGMA foreign_keys = ON")

        return conn

    except sqlite3.Error as e:
        log.error(f"Error al conectar con la BD: {e}")
        raise


def ejecutar_script(ruta_sql: str):
    """
    Ejecuta un archivo .sql o script de migración.
    Se usa durante la inicialización del sistema.
    """
    try:
        with open(ruta_sql, "r", encoding="utf-8") as f:
            script = f.read()

        conn = obtener_conexion()
        conn.executescript(script)
        conn.commit()
        conn.close()
        log.info(f"Script ejecutado correctamente: {ruta_sql}")

    except Exception as e:
        log.error(f"Error ejecutando script {ruta_sql}: {e}")
        raise