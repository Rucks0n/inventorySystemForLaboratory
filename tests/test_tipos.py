"""
tests/test_tipos.py
-------------------
Comprueba los tipos de ítem (Herramienta, Consumible, ...) y que los ítems nuevos
reciban su tipo y unidad.
"""

import unittest

from tests.base_prueba import BaseConBD
from db.migraciones import aplicar_pendientes
from app.controllers.tipos_controller import TiposController
from app.controllers.inventario_controller import DepositosController, InventarioController


class PruebasTipos(BaseConBD):

    def setUp(self):
        super().setUp()
        aplicar_pendientes()
        self.tipos = TiposController()

    def _id_tipo(self, nombre):
        return next(t["id"] for t in self.tipos.obtener_todos() if t["nombre"] == nombre)

    def test_tipos_iniciales(self):
        self.assertEqual([t["nombre"] for t in self.tipos.obtener_todos()],
                         ["Herramienta", "Consumible"])

    def test_agregar_tipo_nuevo(self):
        ok, _ = self.tipos.agregar({"nombre": "Mobiliario", "comportamiento": "presta"})
        self.assertTrue(ok)
        self.assertEqual(len(self.tipos.obtener_todos()), 3)

    def test_rechaza_nombre_repetido_sin_importar_mayusculas(self):
        ok, msg = self.tipos.agregar({"nombre": "consumible", "comportamiento": "consume"})
        self.assertFalse(ok)
        self.assertIn("Ya existe", msg)

    def test_rechaza_comportamiento_invalido_o_nombre_vacio(self):
        self.assertFalse(self.tipos.agregar({"nombre": "X", "comportamiento": "regala"})[0])
        self.assertFalse(self.tipos.agregar({"nombre": "  ", "comportamiento": "presta"})[0])

    def test_el_tipo_por_defecto_es_el_que_se_presta(self):
        self.assertEqual(self.tipos.tipo_por_defecto()["nombre"], "Herramienta")

    def test_no_se_elimina_un_tipo_con_items(self):
        dep_id = self._crear_deposito()
        InventarioController().agregar_item(
            {"deposito_id": dep_id, "nombre": "Aceite", "cantidad_total": 2,
             "tipo_id": self._id_tipo("Consumible"), "unidad": "mL"})
        ok, msg = self.tipos.eliminar(self._id_tipo("Consumible"))
        self.assertFalse(ok)
        self.assertIn("Desactívalo", msg)

    def test_se_elimina_un_tipo_sin_items(self):
        self.tipos.agregar({"nombre": "Temporal", "comportamiento": "presta"})
        ok, _ = self.tipos.eliminar(self._id_tipo("Temporal"))
        self.assertTrue(ok)

    def test_no_se_cambia_comportamiento_con_prestamos_activos(self):
        dep_id = self._crear_deposito()
        self.ejecutar(
            "INSERT INTO items (deposito_id, nombre, cantidad_total, cantidad_disp, cantidad_prest, tipo_id) "
            "VALUES (?, 'Pesa', 2, 1, 1, ?)", (dep_id, self._id_tipo("Herramienta")))
        ok, msg = self.tipos.editar(self._id_tipo("Herramienta"),
                                    {"nombre": "Herramienta", "comportamiento": "consume"})
        self.assertFalse(ok)
        self.assertIn("prestados", msg)

    def test_item_nuevo_usa_tipo_por_defecto_si_no_se_indica(self):
        dep_id = self._crear_deposito()
        ok, _ = InventarioController().agregar_item(
            {"deposito_id": dep_id, "nombre": "Sensor", "cantidad_total": 4})
        self.assertTrue(ok)
        fila = self.consulta("SELECT t.nombre AS tipo, i.unidad FROM items i "
                             "JOIN tipos_item t ON t.id = i.tipo_id")[0]
        self.assertEqual((fila["tipo"], fila["unidad"]), ("Herramienta", None))

    def test_item_nuevo_guarda_tipo_y_unidad_indicados(self):
        dep_id = self._crear_deposito()
        InventarioController().agregar_item(
            {"deposito_id": dep_id, "nombre": "Aceite", "cantidad_total": 500,
             "tipo_id": self._id_tipo("Consumible"), "unidad": " mL "})
        fila = self.consulta("SELECT t.nombre AS tipo, i.unidad FROM items i "
                             "JOIN tipos_item t ON t.id = i.tipo_id")[0]
        self.assertEqual((fila["tipo"], fila["unidad"]), ("Consumible", "mL"))

    def test_la_base_rechaza_un_tipo_que_no_existe(self):
        import sqlite3
        dep_id = self._crear_deposito()
        with self.assertRaises(sqlite3.IntegrityError):
            self.ejecutar("INSERT INTO items (deposito_id, nombre, tipo_id) VALUES (?, 'X', 999)", (dep_id,))

    # ── ayuda ──────────────────────────────────────────────────────────────
    def _crear_deposito(self) -> int:
        DepositosController().agregar({"nombre": "Laboratorio A"})
        return DepositosController().obtener_todos()[0]["id"]


if __name__ == "__main__":
    unittest.main()
