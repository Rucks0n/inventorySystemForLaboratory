"""
tests/test_migraciones.py
-------------------------
Comprueba que las migraciones numeradas se aplican bien, una sola vez,
sin perder datos y sin dejar nada a medias.
"""

import os
import unittest

from tests.base_prueba import BaseConBD
from db.migraciones import aplicar_pendientes, MIGRACIONES
from db.migrations import migration_001


class PruebasMigraciones(BaseConBD):

    def test_base_nueva_queda_completa(self):
        mensajes = aplicar_pendientes()
        self.assertEqual(len(mensajes), len(MIGRACIONES))

        versiones = [f["version"] for f in self.consulta(
            "SELECT version FROM migraciones_aplicadas ORDER BY version")]
        self.assertEqual(versiones, [m[0] for m in MIGRACIONES])

        tipos = [(f["nombre"], f["comportamiento"]) for f in self.consulta(
            "SELECT nombre, comportamiento FROM tipos_item ORDER BY id")]
        self.assertEqual(tipos, [("Herramienta", "presta"), ("Consumible", "consume")])

        columnas = {f["name"] for f in self.consulta("PRAGMA table_info(items)")}
        self.assertTrue({"tipo_id", "unidad"} <= columnas)

    def test_base_nueva_no_crea_respaldo(self):
        aplicar_pendientes()
        self.assertFalse(os.path.exists(self.carpeta_respaldos))

    def test_segunda_vez_no_hace_nada(self):
        aplicar_pendientes()
        self.assertEqual(aplicar_pendientes(), [])

    def test_base_existente_conserva_datos_y_hace_respaldo(self):
        # Simula una instalación anterior: solo existían las tablas base
        migration_001.ejecutar()
        dep = self.ejecutar("INSERT INTO depositos (nombre) VALUES ('Laboratorio A')")
        self.ejecutar("INSERT INTO usuarios (nombre, codigo) VALUES ('Ana', 'U1')")
        item = self.ejecutar(
            "INSERT INTO items (deposito_id, nombre, referencia, cantidad_total, cantidad_disp, "
            "cantidad_prest) VALUES (?, 'Micrómetro', 'M-1', 3, 2, 1)", (dep,))
        self.ejecutar("INSERT INTO items (deposito_id, nombre, cantidad_total, cantidad_disp) "
                      "VALUES (?, 'Sensor', 5, 5)", (dep,))
        self.ejecutar("INSERT INTO prestamos (item_id, usuario_id, cantidad) VALUES (?, 1, 1)", (item,))

        aplicar_pendientes()

        filas = self.consulta("SELECT nombre, cantidad_total, cantidad_prest FROM items ORDER BY id")
        self.assertEqual([tuple(f) for f in filas], [("Micrómetro", 3, 1), ("Sensor", 5, 0)])

        # Los ítems que ya existían quedan como Herramienta
        tipos = {f["nombre"] for f in self.consulta(
            "SELECT t.nombre FROM items i JOIN tipos_item t ON t.id = i.tipo_id")}
        self.assertEqual(tipos, {"Herramienta"})

        self.assertEqual(self.consulta("PRAGMA foreign_key_check"), [])
        self.assertEqual(self.consulta("SELECT COUNT(*) AS n FROM prestamos")[0]["n"], 1)

        respaldos = os.listdir(self.carpeta_respaldos)
        self.assertEqual(len(respaldos), 1)
        self.assertIn("antes_de_migrar", respaldos[0])

    def test_si_una_migracion_falla_no_queda_nada_a_medias(self):
        migration_001.ejecutar()
        # Un objeto con el nombre del índice hace fallar la migración 002 AL FINAL,
        # cuando ya había creado tipos_item y agregado columnas.
        self.ejecutar("CREATE TABLE idx_items_tipo (x INTEGER)")

        with self.assertRaises(Exception):
            aplicar_pendientes()

        self.assertEqual(
            self.consulta("SELECT name FROM sqlite_master WHERE name = 'tipos_item'"), [])
        columnas = {f["name"] for f in self.consulta("PRAGMA table_info(items)")}
        self.assertNotIn("tipo_id", columnas)
        self.assertNotIn("unidad", columnas)

    def test_solo_se_conservan_diez_respaldos(self):
        from db import respaldos
        migration_001.ejecutar()
        for i in range(13):
            respaldos.crear_respaldo(f"prueba{i:02d}")
        self.assertEqual(len(os.listdir(self.carpeta_respaldos)), respaldos.CONSERVAR)


if __name__ == "__main__":
    unittest.main()
