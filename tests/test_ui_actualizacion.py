"""
tests/test_ui_actualizacion.py
------------------------------
Pantallas (Qt en modo "offscreen", sin ventana real):
  - Las columnas Disponible / Prestado se actualizan después de un préstamo.
  - Al eliminar un ítem con historial se avisa, y el historial lo muestra marcado.

Si PyQt6 no está instalado, estas pruebas se saltan.
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
except ImportError:                                           # pragma: no cover
    raise unittest.SkipTest("PyQt6 no está instalado")

from app.controllers.inventario_controller import DepositosController, InventarioController
from app.controllers.prestamos_controller import PrestamosController
from app.ui.inventario_view import InventarioView
from app.ui.main_window import MainWindow
from app.ui.prestamos_view import PrestamosView
from db.migraciones import aplicar_pendientes
from tests.base_prueba import BaseConBD

_app = None
ADMIN = {"id": 1, "nombre": "Admin", "rol": "admin"}


def setUpModule():
    global _app
    _app = QApplication.instance() or QApplication([])


class BasePantallas(BaseConBD):
    def setUp(self):
        super().setUp()
        aplicar_pendientes()
        self.inv, self.pre = InventarioController(), PrestamosController()
        DepositosController().agregar({"nombre": "Lab"})
        self.inv.agregar_item({"deposito_id": 1, "nombre": "Sensor", "referencia": "S-1", "cantidad_total": 5})
        self.inv.agregar_item({"deposito_id": 1, "nombre": "Pesa", "cantidad_total": 2})
        self.ejecutar("INSERT INTO usuarios (nombre, codigo, rol, contrasena) VALUES ('Ana','A1','usuario','x')")

    def abrir(self, clase, *args):
        ventana = clase(*args)
        self.addCleanup(ventana.close)
        ventana.show()
        return ventana

    @staticmethod
    def fila_de(tabla, nombre: str) -> int:
        for fila in range(tabla.rowCount()):
            if nombre in tabla.item(fila, 1).text():
                return fila
        raise AssertionError(f"'{nombre}' no está en la tabla")


class PruebasColumnasDeCantidades(BasePantallas):
    """El error reportado: Disponible y Prestado no cambiaban después de un préstamo."""

    def leer(self, vista: InventarioView, nombre: str) -> tuple[str, str]:
        tabla = vista.tabs_depositos.currentWidget().tabla
        fila = self.fila_de(tabla, nombre)
        return tabla.item(fila, 4).text(), tabla.item(fila, 5).text()      # Disponible, Prestado

    def test_al_volver_a_la_pestana_de_inventario_se_ven_las_cantidades_nuevas(self):
        ventana = self.abrir(MainWindow, ADMIN)
        inventario = ventana.tabs.widget(0)
        self.assertEqual(self.leer(inventario, "Sensor"), ("5", "0"))

        ventana.tabs.setCurrentIndex(1)                                    # va a Préstamos
        self.pre.registrar_prestamo({"item_id": 1, "usuario_id": 1, "cantidad": 2})
        self.assertEqual(self.leer(inventario, "Sensor"), ("5", "0"))      # aún no cambió

        ventana.tabs.setCurrentIndex(0)                                    # vuelve a Inventario
        self.assertEqual(self.leer(inventario, "Sensor"), ("3", "2"))
        self.assertEqual(self.leer(inventario, "Pesa"), ("2", "0"))

    def test_la_devolucion_tambien_se_refleja(self):
        ventana = self.abrir(MainWindow, ADMIN)
        inventario = ventana.tabs.widget(0)
        self.pre.registrar_prestamo({"item_id": 1, "usuario_id": 1, "cantidad": 2})
        ventana.tabs.setCurrentIndex(1)
        ventana.tabs.setCurrentIndex(0)
        self.assertEqual(self.leer(inventario, "Sensor"), ("3", "2"))

        self.pre.registrar_devolucion(1)
        ventana.tabs.setCurrentIndex(1)
        ventana.tabs.setCurrentIndex(0)
        self.assertEqual(self.leer(inventario, "Sensor"), ("5", "0"))

    def test_actualizar_refresca_tambien_la_busqueda_activa(self):
        vista = self.abrir(InventarioView, ADMIN)
        vista.input_buscar.setText("Sensor")
        vista._buscar()
        COLUMNA_DISPONIBLE = 5                  # en los resultados hay una columna "Depósito" más
        tabla = vista.tabs_depositos.currentWidget().tabla
        self.assertEqual(tabla.item(0, COLUMNA_DISPONIBLE).text(), "5")

        self.pre.registrar_prestamo({"item_id": 1, "usuario_id": 1, "cantidad": 1})
        vista.actualizar()
        tabla = vista.tabs_depositos.currentWidget().tabla
        self.assertEqual(tabla.item(0, COLUMNA_DISPONIBLE).text(), "4")

    def test_actualizar_sin_depositos_no_falla(self):
        self.inv.eliminar_item(1)
        self.inv.eliminar_item(2)
        DepositosController().eliminar(1)
        vista = self.abrir(InventarioView, ADMIN)
        vista.actualizar()


class PruebasEliminarDesdeLaPantalla(BasePantallas):

    def setUp(self):
        super().setUp()
        self.preguntas = []                                     # textos de las confirmaciones
        self.enterContext(mock.patch.object(
            QMessageBox, "question",
            side_effect=lambda padre, titulo, texto, *a, **k: (
                self.preguntas.append(texto) or QMessageBox.StandardButton.Yes)))
        self.avisos = []
        self.enterContext(mock.patch.object(
            QMessageBox, "warning",
            side_effect=lambda padre, titulo, texto, *a, **k: self.avisos.append(texto)))

    def seleccionar(self, vista: InventarioView, nombre: str):
        tabla = vista.tabs_depositos.currentWidget().tabla
        tabla.selectRow(self.fila_de(tabla, nombre))

    def test_con_historial_avisa_que_se_conserva_y_elimina(self):
        self.pre.registrar_prestamo({"item_id": 1, "usuario_id": 1, "cantidad": 1})
        self.pre.registrar_devolucion(1)
        vista = self.abrir(InventarioView, ADMIN)
        self.seleccionar(vista, "Sensor")

        vista._eliminar_item()

        self.assertIn("2 movimiento(s)", self.preguntas[0])
        self.assertIn("historial se conserva", self.preguntas[0])
        self.assertEqual(self.avisos, [])
        self.assertIsNone(self.inv.obtener_item_por_id(1))
        tabla = vista.tabs_depositos.currentWidget().tabla
        self.assertEqual([tabla.item(f, 1).text() for f in range(tabla.rowCount())], ["Pesa"])

    def test_sin_historial_no_menciona_el_historial(self):
        vista = self.abrir(InventarioView, ADMIN)
        self.seleccionar(vista, "Pesa")
        vista._eliminar_item()
        self.assertNotIn("historial", self.preguntas[0])
        self.assertIsNone(self.inv.obtener_item_por_id(2))

    def test_con_prestamo_activo_muestra_el_motivo_y_no_elimina(self):
        self.pre.registrar_prestamo({"item_id": 1, "usuario_id": 1, "cantidad": 1})
        vista = self.abrir(InventarioView, ADMIN)
        self.seleccionar(vista, "Sensor")
        vista._eliminar_item()
        self.assertEqual(len(self.avisos), 1)
        self.assertIn("préstamos activos", self.avisos[0])
        self.assertIsNotNone(self.inv.obtener_item_por_id(1))


class PruebasHistorialConItemsEliminados(BasePantallas):

    def setUp(self):
        super().setUp()
        for item_id, prestamo_id in ((1, 1), (2, 2)):
            self.pre.registrar_prestamo({"item_id": item_id, "usuario_id": 1, "cantidad": 1})
            self.pre.registrar_devolucion(prestamo_id)

    def historial(self):
        vista = self.abrir(PrestamosView, ADMIN)
        return vista, vista.tab_historial

    @staticmethod
    def filas(tab) -> dict[str, list[int]]:
        """Filas del historial agrupadas por el nombre del ítem (sin la alerta ⚠)."""
        resultado = {}
        for fila in range(tab.tabla.rowCount()):
            nombre = tab.tabla.item(fila, 3).text().removeprefix("⚠ ")
            resultado.setdefault(nombre, []).append(fila)
        return resultado

    def test_sin_eliminados_no_hay_alerta_ni_color(self):
        _, tab = self.historial()
        self.assertTrue(tab.lbl_aviso.isHidden())
        self.assertEqual(sum(1 for f in range(tab.tabla.rowCount())
                             if tab.tabla.item(f, 3).text().startswith("⚠")), 0)

    def test_el_item_eliminado_aparece_marcado_y_los_demas_no(self):
        self.inv.eliminar_item(1)
        _, tab = self.historial()

        self.assertFalse(tab.lbl_aviso.isHidden())
        filas = self.filas(tab)
        self.assertEqual(len(filas["Sensor"]), 2)
        self.assertEqual(len(filas["Pesa"]), 2)

        for fila in filas["Sensor"]:                          # eliminado: alerta, color y explicación
            celda = tab.tabla.item(fila, 3)
            self.assertTrue(celda.text().startswith("⚠ "))
            self.assertEqual(celda.background().color().name().upper(), "#FFF4D6")
            self.assertIn("ya no está en los depósitos", celda.toolTip())

        for fila in filas["Pesa"]:                            # vigente: sin marca
            celda = tab.tabla.item(fila, 3)
            self.assertFalse(celda.text().startswith("⚠"))
            self.assertEqual(celda.toolTip(), "")
            self.assertNotEqual(celda.background().color().name().upper(), "#FFF4D6")

    def test_conserva_la_referencia_del_item_eliminado(self):
        self.inv.eliminar_item(1)
        _, tab = self.historial()
        fila = self.filas(tab)["Sensor"][0]
        self.assertEqual(tab.tabla.item(fila, 4).text(), "S-1")

    def test_actualizar_refleja_una_eliminacion_hecha_despues(self):
        vista, tab = self.historial()
        self.assertTrue(tab.lbl_aviso.isHidden())
        self.inv.eliminar_item(2)
        vista.actualizar()
        self.assertFalse(tab.lbl_aviso.isHidden())
        self.assertTrue(tab.tabla.item(self.filas(tab)["Pesa"][0], 3).text().startswith("⚠"))
