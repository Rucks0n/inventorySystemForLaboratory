"""
tests/test_importador_ui.py
---------------------------
Prueba el asistente de importación como lo usaría una persona, pero sin pantalla
(Qt en modo "offscreen"): elige un archivo, avanza por los pasos y comprueba qué
quedó en la base de datos.

Si PyQt6 no está instalado, estas pruebas se saltan.
"""

import os
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")        # sin ventana real

try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
except ImportError:                                           # pragma: no cover
    raise unittest.SkipTest("PyQt6 no está instalado")

from app.controllers.inventario_controller import DepositosController
from app.ui.importar import ImportarDialog
from db.migraciones import aplicar_pendientes
from tests.ayuda_importador import crear_xlsx
from tests.base_prueba import BaseConBD

_app = None


def setUpModule():
    global _app
    _app = QApplication.instance() or QApplication([])


class PruebasAsistente(BaseConBD):

    def setUp(self):
        super().setUp()
        aplicar_pendientes()
        DepositosController().agregar({"nombre": "Depósito1"})
        self.avisos = []                                      # textos de los mensajes que se mostraron
        for metodo in ("warning", "information"):
            self.enterContext(mock.patch.object(
                QMessageBox, metodo, side_effect=lambda padre, titulo, texto, *a, **k: self.avisos.append(texto)))
        self.pregunta = self.enterContext(mock.patch.object(
            QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes))

        self.dialogo = ImportarDialog()
        self.addCleanup(self.dialogo.close)
        self.dialogo.show()

    # ── ayudas ─────────────────────────────────────────────────────────────

    def esperar(self, condicion, que, limite=20):
        inicio = time.time()
        while not condicion() and time.time() - inicio < limite:
            _app.processEvents()
            time.sleep(0.01)
        self.assertTrue(condicion(), f"se agotó el tiempo esperando: {que}")

    def abrir(self, hojas, nombre="inventario.xlsx"):
        ruta = crear_xlsx(os.path.join(self._carpeta.name, nombre), hojas)
        self.dialogo.pasos[0].abrir(ruta)
        self.esperar(lambda: self.dialogo.btn_siguiente.isEnabled(), "leer el archivo")

    def siguiente(self):
        self.dialogo._siguiente()
        _app.processEvents()

    def nombres_en_base(self):
        return [f["nombre"] for f in self.consulta("SELECT nombre FROM items ORDER BY nombre")]

    # ── pruebas ────────────────────────────────────────────────────────────

    def test_recorrido_completo_con_dos_hojas_y_una_fila_mala(self):
        self.abrir({"Depósito1": [["Item", "Cant."], ["Sensor", 3], ["Pesa", None]],
                    "Laboratorio A": [["Nombre", "Cantidad"], ["Pinzas", 10]]})
        self.siguiente()                                       # 1 → 2: columnas
        self.assertEqual(self.dialogo.estado.mapeo, {"nombre": "item", "cantidad": "cant"})
        self.siguiente()                                       # 2 → 3: depósitos
        self.dialogo.pasos[2].chk_crear.setChecked(True)       # «Laboratorio A» todavía no existe
        self.siguiente()                                       # 3 → 4: revisión
        self.esperar(lambda: self.dialogo.estado.analisis is not None, "revisar el archivo")

        analisis = self.dialogo.estado.analisis
        self.assertEqual((len(analisis.filas), analisis.filas_con_error), (2, 1))
        self.assertEqual(self.nombres_en_base(), [])           # revisar NO guarda nada
        self.assertIn("solo lo correcto", self.dialogo.btn_siguiente.text())

        self.siguiente()                                       # 4 → 5: guardar
        self.pregunta.assert_called_once()                     # avisó que hay filas con problemas
        self.esperar(lambda: self.dialogo.pasos[4].terminado, "guardar")
        self.assertEqual(self.nombres_en_base(), ["Pinzas", "Sensor"])
        self.assertEqual(self.dialogo.estado.resultado.depositos_creados, ["Laboratorio A"])
        self.assertTrue(self.dialogo.hubo_cambios)
        self.assertEqual(self.dialogo.btn_cancelar.text(), "Cerrar")

    def test_si_el_usuario_responde_que_no_a_importar_solo_lo_correcto_no_avanza(self):
        self.pregunta.return_value = QMessageBox.StandardButton.No
        self.abrir({"Depósito1": [["Nombre", "Cantidad"], ["Sensor", 3], ["Pesa", "muchas"]]})
        for _ in range(3):
            self.siguiente()
        self.esperar(lambda: self.dialogo.estado.analisis is not None, "revisar el archivo")
        self.siguiente()
        self.assertEqual(self.dialogo._indice, 3)              # se quedó en la revisión
        self.assertEqual(self.nombres_en_base(), [])

    def test_cerrar_en_la_revision_no_deja_nada_guardado(self):
        self.abrir({"Depósito1": [["Nombre", "Cantidad"], ["Sensor", 3]]})
        for _ in range(3):
            self.siguiente()
        self.esperar(lambda: self.dialogo.estado.analisis is not None, "revisar el archivo")
        self.dialogo.reject()
        self.assertEqual(self.nombres_en_base(), [])
        self.assertFalse(self.dialogo.hubo_cambios)

    def test_un_archivo_que_no_se_puede_leer_se_explica_y_no_deja_avanzar(self):
        viejo = os.path.join(self._carpeta.name, "viejo.xls")
        open(viejo, "wb").close()
        self.dialogo.pasos[0].abrir(viejo)
        self.esperar(lambda: self.avisos, "recibir el aviso de error")
        self.assertIn(".xlsx", self.avisos[0])
        self.assertFalse(self.dialogo.btn_siguiente.isEnabled())

    def test_hojas_que_no_parecen_inventario_vienen_desmarcadas(self):
        self.abrir({"Depósito1": [["Nombre", "Cantidad"], ["Sensor", 3]],
                    "Notas": [["Recordar comprar guantes"]]})
        lista = self.dialogo.pasos[0].lista
        marcadas = {lista.item(i).text().split("  ")[0]: lista.item(i).checkState().name
                    for i in range(lista.count())}
        self.assertEqual(marcadas, {"Depósito1": "Checked", "Notas": "Unchecked"})

    def test_falta_una_columna_obligatoria_avisa_y_no_avanza(self):
        self.abrir({"Depósito1": [["Nombre", "Lo que sea"], ["Sensor", 3]]})
        self.siguiente()                                       # 1 → 2
        self.siguiente()                                       # intenta 2 → 3 sin columna de cantidad
        self.assertEqual(self.dialogo._indice, 1)
        self.assertIn("Cantidad", self.avisos[-1])

    def test_volver_atras_y_cambiar_las_opciones_se_nota_en_la_revision(self):
        self.abrir({"Depósito1": [["Nombre", "Cantidad"], ["Sensor", 3]]})
        for _ in range(3):
            self.siguiente()
        self.esperar(lambda: self.dialogo.estado.analisis is not None, "primera revisión")
        self.assertEqual(len(self.dialogo.estado.plan.crear), 1)

        self.dialogo._atras()                                  # de vuelta al paso 3
        self.dialogo.pasos[2].rb_unico.setChecked(True)
        self.dialogo.pasos[2].combo_unico.setEditText("Bodega nueva")
        self.dialogo.pasos[2].chk_crear.setChecked(True)
        self.siguiente()
        self.esperar(lambda: self.dialogo.estado.analisis is not None, "segunda revisión")
        self.assertEqual(self.dialogo.estado.plan.depositos_nuevos, ["Bodega nueva"])
        self.assertEqual([f.deposito for f in self.dialogo.estado.analisis.filas], ["Bodega nueva"])


if __name__ == "__main__":
    unittest.main()
