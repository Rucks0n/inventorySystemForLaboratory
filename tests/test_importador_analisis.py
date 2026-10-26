"""
tests/test_importador_analisis.py
---------------------------------
Pruebas de la revisión del archivo (analizador): qué filas pasan, cuáles se rechazan
y por qué, y cómo se reparten los ítems entre depósitos. Nada de esto guarda en la base.
"""

import os
import unittest

from app.controllers.inventario_controller import DepositosController
from app.services.importador.analizador import analizar
from app.services.importador.catalogo import cargar_catalogo
from app.services.importador.modelos import ConfigImportacion, ErrorImportacion, ImportacionCancelada
from config.constants import (
    IMP_AVISO, IMP_DEPOSITO_POR_COLUMNA, IMP_DEPOSITO_POR_HOJA, IMP_DEPOSITO_UNICO, IMP_ERROR,
)
from db.migraciones import aplicar_pendientes
from tests.ayuda_importador import analizar_hojas, crear_xlsx
from tests.base_prueba import BaseConBD


class BaseAnalisis(BaseConBD):
    def setUp(self):
        super().setUp()
        aplicar_pendientes()
        for nombre in ("Depósito1", "Laboratorio A"):
            DepositosController().agregar({"nombre": nombre})
        self.carpeta = self._carpeta.name

    def analizar(self, hojas, **config):
        return analizar_hojas(self.carpeta, hojas, **config)

    def tipo_id(self, nombre):
        return next(t.id for t in cargar_catalogo().tipos_por_id.values() if t.nombre == nombre)

    @staticmethod
    def mensajes(analisis, nivel=None, fila=None):
        return [i.mensaje for i in analisis.incidencias
                if (nivel is None or i.nivel == nivel) and (fila is None or i.fila == fila)]


class PruebasLecturaDeColumnas(BaseAnalisis):

    def test_encabezado_debajo_de_titulos(self):
        a = self.analizar({"Depósito1": [
            ["INVENTARIO DEL LABORATORIO"], [], ["Fecha:", "19/10"],
            ["Item", "Cant.", "Ubicación"],
            ["Micrómetro", 3, "E1"],
            ["Pesa 100 g", 5, "E2"],
        ]})
        self.assertEqual([(f.nombre, f.cantidad, f.ubicacion, f.fila) for f in a.filas],
                         [("Micrómetro", 3, "E1", 5), ("Pesa 100 g", 5, "E2", 6)])
        self.assertEqual(a.incidencias, [])

    def test_distinto_orden_de_columnas_entre_hojas(self):
        a = self.analizar(
            {"Depósito1": [["Nombre", "Cantidad", "Código"], ["Sensor", 4, "S-1"]],
             "Laboratorio A": [["Cantidad", "Código", "Nombre"], [7, "T-9", "Termómetro"]]})
        self.assertEqual(sorted((f.deposito, f.nombre, f.cantidad, f.referencia) for f in a.filas),
                         [("Depósito1", "Sensor", 4, "S-1"), ("Laboratorio A", "Termómetro", 7, "T-9")])

    def test_un_excel_sin_codigo_ni_detalles_tambien_se_lee(self):
        a = self.analizar({"Depósito1": [["Nombre", "Cantidad"], ["Aceite", 3]]})
        f = a.filas[0]
        self.assertEqual((f.nombre, f.cantidad, f.referencia, f.observaciones, f.ubicacion),
                         ("Aceite", 3, None, None, None))

    def test_los_codigos_numericos_no_quedan_como_1_punto_0(self):
        a = self.analizar({"Depósito1": [["Nombre", "Cantidad", "Código"], ["Sensor", 4, 101.0]]})
        self.assertEqual(a.filas[0].referencia, "101")

    def test_una_hoja_sin_la_columna_obligatoria_se_omite_y_las_demas_siguen(self):
        a = self.analizar(
            {"Depósito1": [["Nombre", "Cantidad"], ["Sensor", 4]],
             "Laboratorio A": [["Nombre", "Existencias raras"], ["Pesa", 1]]},
            mapeo={"nombre": "nombre", "cantidad": "cantidad"})
        self.assertEqual([f.nombre for f in a.filas], ["Sensor"])
        self.assertEqual(a.hojas_omitidas, 1)
        self.assertIn("no tiene la columna «cantidad»", self.mensajes(a, IMP_ERROR)[0])

    def test_una_columna_opcional_ausente_en_una_hoja_solo_avisa(self):
        a = self.analizar(
            {"Depósito1": [["Nombre", "Cantidad", "Código"], ["Sensor", 4, "S-1"]],
             "Laboratorio A": [["Nombre", "Cantidad"], ["Pesa", 1]]})
        self.assertEqual(len(a.filas), 2)
        self.assertEqual(self.mensajes(a, IMP_AVISO)[0].count("«codigo»"), 1)

    def test_las_columnas_opcionales_que_faltan_se_avisan_en_un_solo_mensaje_por_hoja(self):
        a = self.analizar(
            {"Depósito1": [["Nombre", "Cantidad", "Código", "Ubicación", "Observaciones"], ["Sensor", 4, "S-1", "E1", "ok"]],
             "Laboratorio A": [["Nombre", "Cantidad"], ["Pinzas", 10]]})
        avisos = self.mensajes(a, IMP_AVISO)
        self.assertEqual(len(avisos), 1)
        for columna in ("«codigo»", "«ubicacion»", "«observaciones»"):
            self.assertIn(columna, avisos[0])

    def test_la_columna_de_deposito_se_ignora_si_el_deposito_viene_de_la_hoja(self):
        a = self.analizar(
            {"Depósito1": [["Nombre", "Cantidad", "Laboratorio"], ["Sensor", 4, "Depósito1"]],
             "Laboratorio A": [["Nombre", "Cantidad"], ["Pinzas", 10]]},
            modo_deposito=IMP_DEPOSITO_POR_HOJA)
        self.assertEqual(len(a.filas), 2)
        self.assertEqual(self.mensajes(a, IMP_AVISO), [])
        self.assertEqual(a.hojas_omitidas, 0)

    def test_una_hoja_con_otros_nombres_de_columna_se_lee_y_avisa(self):
        a = self.analizar(
            {"Depósito1": [["Item", "Cant."], ["Sensor", 4]],
             "Laboratorio A": [["Nombre", "Cantidad"], ["Pinzas", 10]]})
        self.assertEqual(sorted((f.deposito, f.nombre, f.cantidad) for f in a.filas),
                         [("Depósito1", "Sensor", 4), ("Laboratorio A", "Pinzas", 10)])
        avisos = self.mensajes(a, IMP_AVISO)
        self.assertEqual(len(avisos), 2)                       # uno por columna que se buscó sola
        self.assertTrue(all("«Nombre»" in m or "«Cantidad»" in m for m in avisos))
        self.assertEqual(a.hojas_omitidas, 0)

    def test_no_se_reutiliza_una_columna_que_ya_tiene_otro_dato(self):
        # En la 2.ª hoja "Descripción" ya es observaciones: no puede pasar a ser también el nombre.
        a = self.analizar(
            {"Depósito1": [["Item", "Cant.", "Descripción"], ["Sensor", 4, "digital"]],
             "Laboratorio A": [["Descripción", "Cantidad"], ["algo", 10]]})
        self.assertEqual([f.nombre for f in a.filas], ["Sensor"])
        self.assertEqual(a.hojas_omitidas, 1)
        self.assertEqual(self.mensajes(a, IMP_AVISO), [])      # y sin avisos sueltos de la hoja omitida

    def test_configuracion_incompleta(self):
        ruta = crear_xlsx(os.path.join(self.carpeta, "a.xlsx"), {"Depósito1": [["Nombre", "Cantidad"]]})
        casos = [
            ConfigImportacion(ruta=ruta, hojas=[], mapeo={"nombre": "nombre", "cantidad": "cantidad"}),
            ConfigImportacion(ruta=ruta, hojas=["Depósito1"], mapeo={"nombre": "nombre"}),
            ConfigImportacion(ruta=ruta, hojas=["Depósito1"], mapeo={"nombre": "nombre", "cantidad": "cantidad"},
                              modo_deposito=IMP_DEPOSITO_UNICO),
            ConfigImportacion(ruta=ruta, hojas=["Depósito1"], mapeo={"nombre": "nombre", "cantidad": "cantidad"},
                              modo_deposito=IMP_DEPOSITO_POR_COLUMNA),
        ]
        for cfg in casos:
            with self.assertRaises(ErrorImportacion):
                analizar(cfg, cargar_catalogo())


class PruebasValidacionDeFilas(BaseAnalisis):

    def test_cada_error_se_explica_y_solo_se_rechaza_esa_fila(self):
        a = self.analizar({"Depósito1": [
            ["Nombre", "Cantidad", "Tipo"],
            ["Bueno", 5, None],                      # 2  ok
            [None, 3, None],                         # 3  sin nombre
            ["Sin cantidad", None, None],            # 4
            ["Decimal", 2.5, None],                  # 5
            ["Texto", "10 mL", None],                # 6
            ["Negativo", -1, None],                  # 7
            ["Tipo raro", 1, "Mueble"],              # 8
            ["Roto", "#REF!", None],                 # 9
            ["Total", 99, None],                     # 10 fila de totales
            ["x" * 201, 1, None],                    # 11 nombre larguísimo
            ["Otro bueno", 0, "Consumible"],         # 12 cantidad 0 es válida
        ]})
        self.assertEqual([f.nombre for f in a.filas], ["Bueno", "Otro bueno"])
        self.assertEqual(a.filas_con_error, 9)
        esperado = {3: "Falta el nombre", 4: "vacía", 5: "decimales", 6: "no es un número",
                    7: "negativa", 8: "no existe", 9: "error de Excel", 10: "totales", 11: "demasiado largo"}
        for fila, parte in esperado.items():
            self.assertIn(parte, " ".join(self.mensajes(a, IMP_ERROR, fila)), f"fila {fila}")
        self.assertIn("Herramienta, Consumible", self.mensajes(a, IMP_ERROR, 8)[0])

    def test_filas_vacias_se_ignoran_sin_ruido(self):
        a = self.analizar({"Depósito1": [["Nombre", "Cantidad"], ["A", 1], [], [None, None], ["B", 2]]})
        self.assertEqual((len(a.filas), len(a.incidencias), a.leidas), (2, 0, 2))

    def test_se_guarda_el_contenido_original_de_las_filas_con_problemas(self):
        a = self.analizar({"Depósito1": [["Nombre", "Cantidad"], ["Roto", "abc"]]})
        self.assertEqual(a.originales[("Depósito1", 2)], ["Roto", "abc"])

    def test_repetidos_en_el_archivo(self):
        a = self.analizar({"Depósito1": [
            ["Nombre", "Cantidad", "Referencia"],
            ["Cable USB", 5, "A"],                   # 2
            ["cable  usb", 3, "a"],                  # 3  mismo (ignora mayúsculas y espacios)
            ["Cable USB", 2, "B"],                   # 4  otra referencia = otro ítem
            ["Cable USB", 1, None],                  # 5  sin referencia = otro ítem
        ]})
        self.assertEqual([f.fila for f in a.filas], [2, 4, 5])
        self.assertIn("igual a la fila 2", self.mensajes(a, IMP_ERROR, 3)[0])

    def test_el_mismo_nombre_en_depositos_distintos_no_es_repetido(self):
        a = self.analizar({"Depósito1": [["Nombre", "Cantidad"], ["Pesa", 1]],
                           "Laboratorio A": [["Nombre", "Cantidad"], ["Pesa", 2]]})
        self.assertEqual(len(a.filas), 2)


class PruebasTipoYUnidad(BaseAnalisis):

    def test_tipo_por_columna_y_tipo_por_defecto(self):
        a = self.analizar({"Depósito1": [["Nombre", "Cantidad", "Tipo", "Unidad"],
                                         ["Micrómetro", 1, "herramienta", None],
                                         ["Aceite", 500, "CONSUMIBLE", "mL"],
                                         ["Pesa", 2, None, None]]},
                          tipo_defecto_id=self.tipo_id("Herramienta"))
        self.assertEqual([(f.nombre, f.tipo_id, f.unidad) for f in a.filas],
                         [("Micrómetro", self.tipo_id("Herramienta"), None),
                          ("Aceite", self.tipo_id("Consumible"), "mL"),
                          ("Pesa", None, None)])          # sin tipo en el archivo: se aplica el por defecto al guardar
        self.assertEqual(a.incidencias, [])

    def test_consumible_sin_unidad_es_un_aviso_no_un_error(self):
        a = self.analizar({"Depósito1": [["Nombre", "Cantidad", "Tipo"], ["Grafito", 10, "Consumible"]]})
        self.assertEqual(len(a.filas), 1)
        self.assertIn("sin unidad", self.mensajes(a, IMP_AVISO, 2)[0])

    def test_el_aviso_de_unidad_tambien_aplica_con_tipo_por_defecto_consumible(self):
        a = self.analizar({"Depósito1": [["Nombre", "Cantidad"], ["Grafito", 10]]},
                          tipo_defecto_id=self.tipo_id("Consumible"))
        self.assertIn("sin unidad", self.mensajes(a, IMP_AVISO, 2)[0])


class PruebasDepositos(BaseAnalisis):

    def test_cada_hoja_es_un_deposito_sin_importar_tildes_ni_espacios(self):
        a = self.analizar({"deposito 1": [["Nombre", "Cantidad"], ["A", 1]],
                           "LABORATORIO_A": [["Nombre", "Cantidad"], ["B", 1]]})
        self.assertEqual([(f.nombre, f.deposito) for f in a.filas],
                         [("A", "Depósito1"), ("B", "Laboratorio A")])      # nombres oficiales

    def test_hoja_sin_deposito_existente_no_se_importa_salvo_que_se_permita_crearlo(self):
        hojas = {"Depósito1": [["Nombre", "Cantidad"], ["A", 1]],
                 "Bodega Nueva": [["Nombre", "Cantidad"], ["B", 1]]}
        sin_permiso = self.analizar(hojas)
        self.assertEqual([f.nombre for f in sin_permiso.filas], ["A"])
        self.assertIn("no existe", self.mensajes(sin_permiso, IMP_ERROR, 0)[0])
        self.assertEqual(sin_permiso.depositos_nuevos, [])

        con_permiso = self.analizar(hojas, crear_depositos=True)
        self.assertEqual([(f.nombre, f.deposito) for f in con_permiso.filas],
                         [("A", "Depósito1"), ("B", "Bodega Nueva")])
        self.assertEqual(con_permiso.depositos_nuevos, ["Bodega Nueva"])

    def test_deposito_en_una_columna_con_celdas_combinadas(self):
        """En Excel es común combinar la celda del depósito hacia abajo: solo la primera trae el nombre."""
        a = self.analizar({"Todo": [
            ["Depósito", "Nombre", "Cantidad"],
            ["Depósito1", "A", 1],
            [None, "B", 2],                      # combinada: sigue siendo Depósito1
            ["laboratorio a", "C", 3],           # se escribe distinto: se reconoce igual
            [None, "D", 4],
        ]}, modo_deposito=IMP_DEPOSITO_POR_COLUMNA)
        self.assertEqual([(f.nombre, f.deposito) for f in a.filas],
                         [("A", "Depósito1"), ("B", "Depósito1"), ("C", "Laboratorio A"), ("D", "Laboratorio A")])

    def test_deposito_en_columna_vacio_desde_el_principio_es_error(self):
        a = self.analizar({"Todo": [["Depósito", "Nombre", "Cantidad"], [None, "A", 1]]},
                          modo_deposito=IMP_DEPOSITO_POR_COLUMNA)
        self.assertEqual(a.filas, [])
        self.assertIn("Falta el depósito", self.mensajes(a, IMP_ERROR, 2)[0])

    def test_deposito_en_columna_que_no_existe_se_rechaza_fila_por_fila(self):
        a = self.analizar({"Todo": [["Depósito", "Nombre", "Cantidad"],
                                    ["Depósito1", "A", 1], ["Fantasma", "B", 2]]},
                          modo_deposito=IMP_DEPOSITO_POR_COLUMNA)
        self.assertEqual([f.nombre for f in a.filas], ["A"])
        self.assertIn("«Fantasma» no existe", self.mensajes(a, IMP_ERROR, 3)[0])

    def test_todo_el_archivo_a_un_solo_deposito(self):
        a = self.analizar({"Hoja1": [["Nombre", "Cantidad"], ["A", 1]], "Hoja2": [["Nombre", "Cantidad"], ["B", 2]]},
                          modo_deposito=IMP_DEPOSITO_UNICO, deposito_unico="laboratorio a")
        self.assertEqual({f.deposito for f in a.filas}, {"Laboratorio A"})
        self.assertEqual(len(a.filas), 2)

    def test_el_mismo_nombre_en_dos_hojas_del_mismo_deposito_unico_se_detecta(self):
        a = self.analizar({"Hoja1": [["Nombre", "Cantidad"], ["A", 1]], "Hoja2": [["Nombre", "Cantidad"], ["A", 2]]},
                          modo_deposito=IMP_DEPOSITO_UNICO, deposito_unico="Depósito1")
        self.assertEqual(len(a.filas), 1)
        self.assertIn("de la hoja «Hoja1»", self.mensajes(a, IMP_ERROR, 2)[0])

    def test_depositos_nuevos_no_se_repiten_aunque_aparezcan_escritos_distinto(self):
        a = self.analizar({"Todo": [["Depósito", "Nombre", "Cantidad"],
                                    ["Bodega Nueva", "A", 1], ["bodega  nueva", "B", 1], ["BODEGA-NUEVA", "C", 1]]},
                          modo_deposito=IMP_DEPOSITO_POR_COLUMNA, crear_depositos=True)
        self.assertEqual(a.depositos_nuevos, ["Bodega Nueva"])
        self.assertEqual({f.deposito for f in a.filas}, {"Bodega Nueva"})


class PruebasRendimiento(BaseAnalisis):

    def test_el_libro_se_abre_una_sola_vez_aunque_tenga_muchas_hojas(self):
        """Abrir un Excel grande es lo más caro: se paga el libro completo en cada apertura."""
        import openpyxl
        from unittest import mock
        hojas = {f"H{i}": [["Nombre", "Cantidad"], [f"Ítem {i}", i]] for i in range(1, 7)}
        with mock.patch("app.services.importador.lector.openpyxl.load_workbook",
                        wraps=openpyxl.load_workbook) as abrir:
            a = self.analizar(hojas, modo_deposito=IMP_DEPOSITO_UNICO, deposito_unico="Depósito1")
        self.assertEqual(len(a.filas), 6)
        self.assertEqual(abrir.call_count, 2)          # 1 para adivinar las columnas (la prueba) + 1 el análisis


class PruebasProgresoYCancelacion(BaseAnalisis):

    def test_informa_el_avance_y_se_puede_cancelar(self):
        filas = [["Nombre", "Cantidad"]] + [[f"Ítem {i}", i] for i in range(1, 1201)]
        ruta = crear_xlsx(os.path.join(self.carpeta, "grande.xlsx"), {"Depósito1": filas})
        cfg = ConfigImportacion(ruta=ruta, hojas=["Depósito1"], mapeo={"nombre": "nombre", "cantidad": "cantidad"})

        avances = []
        a = analizar(cfg, cargar_catalogo(), progreso=lambda msg, hecho, total: avances.append(hecho))
        self.assertEqual(len(a.filas), 1200)
        self.assertEqual(avances, [500, 1000])

        with self.assertRaises(ImportacionCancelada):
            analizar(cfg, cargar_catalogo(), cancelado=lambda: True)


if __name__ == "__main__":
    unittest.main()
