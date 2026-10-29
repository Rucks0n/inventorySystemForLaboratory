"""
tests/test_items_eliminados.py
------------------------------
Eliminar un ítem que ya tiene historial: el ítem sale de los depósitos pero su
historial se conserva (migración 004).
"""

from unittest import mock

from app.controllers.inventario_controller import DepositosController, InventarioController
from app.controllers.prestamos_controller import PrestamosController
from db import migraciones
from db.migraciones import MIGRACIONES, aplicar_pendientes
from db.migrations import migration_004
from tests.base_prueba import BaseConBD


class BaseItems(BaseConBD):
    def setUp(self):
        super().setUp()
        aplicar_pendientes()
        self.inv, self.pre = InventarioController(), PrestamosController()
        DepositosController().agregar({"nombre": "Lab"})
        self.inv.agregar_item({"deposito_id": 1, "nombre": "Sensor", "referencia": "S-1", "cantidad_total": 5})
        self.inv.agregar_item({"deposito_id": 1, "nombre": "Pesa", "cantidad_total": 2})
        self.ejecutar("INSERT INTO usuarios (nombre, codigo, rol, contrasena) VALUES ('Ana','A1','usuario','x')")

    def prestar_y_devolver(self, item_id: int, prestamo_id: int):
        self.pre.registrar_prestamo({"item_id": item_id, "usuario_id": 1, "cantidad": 1})
        self.pre.registrar_devolucion(prestamo_id)


class PruebasEliminarConHistorial(BaseItems):

    def setUp(self):
        super().setUp()
        self.prestar_y_devolver(1, 1)           # Sensor: 1 salida + 1 devolución
        self.prestar_y_devolver(2, 2)           # Pesa: 1 salida + 1 devolución

    def test_contar_historial(self):
        self.assertEqual(self.inv.contar_historial(1), 2)
        self.assertEqual(self.inv.contar_historial(999), 0)

    def test_se_puede_eliminar_y_sale_del_inventario(self):
        self.assertEqual(self.inv.eliminar_item(1), (True, ""))
        self.assertIsNone(self.inv.obtener_item_por_id(1))
        self.assertEqual([i["nombre"] for i in self.inv.obtener_todos_los_items()], ["Pesa"])

    def test_el_historial_se_conserva_con_el_nombre(self):
        antes = len(self.pre.obtener_historial())
        self.inv.eliminar_item(1)
        historial = self.pre.obtener_historial()
        self.assertEqual(len(historial), antes)

        del_sensor = [m for m in historial if m["item_nombre"] == "Sensor"]
        self.assertEqual({m["tipo"] for m in del_sensor}, {"Salida", "Devolución"})
        self.assertTrue(all(m["item_eliminado"] == 1 and m["item_ref"] == "S-1" for m in del_sensor))

    def test_los_demas_items_no_se_marcan(self):
        self.inv.eliminar_item(1)
        de_la_pesa = [m for m in self.pre.obtener_historial() if m["item_nombre"] == "Pesa"]
        self.assertEqual(len(de_la_pesa), 2)
        self.assertTrue(all(m["item_eliminado"] == 0 for m in de_la_pesa))

    def test_sin_eliminar_nada_se_marca(self):
        self.assertTrue(all(m["item_eliminado"] == 0 for m in self.pre.obtener_historial()))

    def test_no_quedan_registros_huerfanos(self):
        self.inv.eliminar_item(1)
        self.assertEqual(self.consulta("PRAGMA foreign_key_check"), [])
        self.assertEqual(self.consulta("SELECT COUNT(*) AS n FROM prestamos WHERE item_id = 1")[0]["n"], 0)
        self.assertEqual(self.consulta("SELECT COUNT(*) AS n FROM devoluciones WHERE item_id = 1")[0]["n"], 0)
        # el detalle del otro ítem sigue completo
        self.assertEqual(self.consulta("SELECT COUNT(*) AS n FROM prestamos WHERE item_id = 2")[0]["n"], 1)
        self.assertEqual(self.consulta("SELECT COUNT(*) AS n FROM devoluciones WHERE item_id = 2")[0]["n"], 1)

    def test_el_nombre_guardado_es_el_de_cuando_se_elimino(self):
        self.inv.editar_item(1, {"nombre": "Sensor ultrasónico", "cantidad_total": 5})
        self.inv.eliminar_item(1)
        nombres = {m["item_nombre"] for m in self.pre.obtener_historial() if m["item_eliminado"]}
        self.assertEqual(nombres, {"Sensor ultrasónico"})

    def test_un_item_nuevo_con_el_mismo_nombre_no_hereda_el_historial(self):
        self.inv.eliminar_item(1)
        self.inv.agregar_item({"deposito_id": 1, "nombre": "Sensor", "cantidad_total": 1})
        nuevo = [i for i in self.inv.obtener_todos_los_items() if i["nombre"] == "Sensor"][0]
        self.assertEqual(self.inv.contar_historial(nuevo["id"]), 0)
        self.assertEqual(sum(m["item_eliminado"] for m in self.pre.obtener_historial()), 2)

    def test_se_pueden_eliminar_todos_y_el_historial_sigue_completo(self):
        self.inv.eliminar_item(1)
        self.inv.eliminar_item(2)
        self.assertEqual(self.inv.obtener_todos_los_items(), [])
        self.assertEqual(len(self.pre.obtener_historial()), 4)
        self.assertEqual(self.consulta("PRAGMA foreign_key_check"), [])


class PruebasEliminarBloqueos(BaseItems):

    def test_con_prestamo_activo_no_se_elimina_y_no_se_toca_nada(self):
        self.pre.registrar_prestamo({"item_id": 1, "usuario_id": 1, "cantidad": 2})
        ok, msg = self.inv.eliminar_item(1)
        self.assertFalse(ok)
        self.assertIn("préstamos activos", msg)

        self.assertIsNotNone(self.inv.obtener_item_por_id(1))
        self.assertEqual(self.inv.contar_historial(1), 1)          # sigue enlazado al ítem
        self.assertEqual(len(self.pre.obtener_activos()), 1)
        self.assertEqual(self.pre.obtener_historial()[0]["item_eliminado"], 0)

    def test_devuelto_el_prestamo_ya_se_puede_eliminar(self):
        self.pre.registrar_prestamo({"item_id": 1, "usuario_id": 1, "cantidad": 2})
        self.pre.registrar_devolucion(1)
        self.assertEqual(self.inv.eliminar_item(1), (True, ""))

    def test_item_sin_historial_se_elimina_igual(self):
        self.assertEqual(self.inv.eliminar_item(2), (True, ""))
        self.assertEqual(self.pre.obtener_historial(), [])


class PruebasMigracion004(BaseConBD):

    def test_se_puede_repetir_sin_dano(self):
        aplicar_pendientes()
        migration_004.ejecutar()
        migration_004.ejecutar()
        disparadores = self.consulta("SELECT name FROM sqlite_master WHERE type = 'trigger'")
        self.assertEqual([d["name"] for d in disparadores], ["items_antes_de_eliminar"])

    def test_actualiza_una_base_con_datos_y_el_historial_viejo_tambien_se_conserva(self):
        # Una base que llegó hasta la migración 3, con historial ya registrado
        with mock.patch.object(migraciones, "MIGRACIONES", MIGRACIONES[:3]):
            aplicar_pendientes()
        columnas = {f["name"] for f in self.consulta("PRAGMA table_info(movimientos)")}
        self.assertNotIn("item_nombre", columnas)

        inv = InventarioController()
        DepositosController().agregar({"nombre": "Lab"})
        inv.agregar_item({"deposito_id": 1, "nombre": "Micrómetro", "cantidad_total": 3})
        self.ejecutar("INSERT INTO usuarios (nombre, codigo, rol, contrasena) VALUES ('Ana','A1','usuario','x')")
        pre = PrestamosController()
        pre.registrar_prestamo({"item_id": 1, "usuario_id": 1, "cantidad": 1})
        pre.registrar_devolucion(1)

        self.assertEqual(len(aplicar_pendientes()), 1)              # solo la migración 4

        self.assertEqual(inv.eliminar_item(1), (True, ""))
        historial = pre.obtener_historial()
        self.assertEqual(len(historial), 2)
        self.assertTrue(all(m["item_nombre"] == "Micrómetro" and m["item_eliminado"] == 1 for m in historial))
        self.assertEqual(self.consulta("PRAGMA foreign_key_check"), [])
