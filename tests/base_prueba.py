"""
tests/base_prueba.py
--------------------
Ayuda común para las pruebas: cada prueba trabaja con una base SQLite
temporal y vacía, así que nunca toca tu base real (db/inventario.db).

Cómo correr todas las pruebas (desde la carpeta raíz del proyecto):
    py -m unittest discover -s tests -t .
"""

import os
import tempfile
import unittest

from db import database


class BaseConBD(unittest.TestCase):
    """Hereda de esta clase para tener una base temporal en self.ruta_bd."""

    def setUp(self):
        self._carpeta = tempfile.TemporaryDirectory()
        self.ruta_bd  = os.path.join(self._carpeta.name, "prueba.db")
        self._ruta_original = database.DB_RUTA
        database.DB_RUTA = self.ruta_bd          # todo el sistema usa ahora la base temporal

    def tearDown(self):
        database.DB_RUTA = self._ruta_original
        self._carpeta.cleanup()

    # ── atajos ─────────────────────────────────────────────────────────────
    def conexion(self):
        return database.obtener_conexion()

    def consulta(self, sql: str, params: tuple = ()):
        """Ejecuta un SELECT y devuelve todas las filas."""
        conn = self.conexion()
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def ejecutar(self, sql: str, params: tuple = ()):
        """Ejecuta un INSERT/UPDATE y guarda el cambio."""
        conn = self.conexion()
        try:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @property
    def carpeta_respaldos(self) -> str:
        return os.path.join(self._carpeta.name, "respaldos")
