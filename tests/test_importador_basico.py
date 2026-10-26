"""
tests/test_importador_basico.py
-------------------------------
Pruebas de las piezas pequeñas del importador que no necesitan archivos ni base:
limpieza de texto, lectura de cantidades y reconocimiento de columnas.
"""

import unittest

from app.services.importador.analizador import parsear_cantidad
from app.services.importador.mapeo import (
    adivinar_mapeo, campos_faltantes, columnas_sin_usar, detectar_fila_encabezado,
    mapeo_de_perfil, proponer_mapeo, resolver_indices,
)
from app.services.importador.texto import clave, limpiar, normalizar


class PruebasTexto(unittest.TestCase):

    def test_normalizar_quita_tildes_mayusculas_y_signos(self):
        self.assertEqual(normalizar("  Micrómetro (0-25)mm "), "micrometro 0 25 mm")
        self.assertEqual(normalizar(None), "")

    def test_clave_de_deposito_ignora_espacios_y_signos(self):
        for escrito in ("Depósito 1", "deposito_1", "DEPÓSITO1", "Deposito-1"):
            self.assertEqual(clave(escrito), "deposito1")

    def test_limpiar(self):
        self.assertEqual(limpiar(1.0), "1")                     # el 1.0 de Excel no debe llegar a la base
        self.assertEqual(limpiar(7), "7")
        self.assertEqual(limpiar("  a   b \xa0"), "a b")
        self.assertEqual(limpiar("﻿nombre"), "nombre")
        self.assertIsNone(limpiar("   "))
        self.assertIsNone(limpiar(None))
        self.assertEqual(limpiar("x\n\n  y", una_linea=False), "x\n\ny")


class PruebasCantidad(unittest.TestCase):

    def test_cantidades_validas(self):
        for valor, esperado in [(5, 5), (0, 0), (5.0, 5), ("5", 5), (" 12 ", 12),
                                ("5.0", 5), ("5,00", 5), ("\xa07", 7)]:
            self.assertEqual(parsear_cantidad(valor), (esperado, None), valor)

    def test_cantidades_rechazadas_con_motivo_claro(self):
        casos = [
            (None, "vacía"), ("", "vacía"), ("  ", "vacía"),
            (2.5, "decimales"), ("1,5", "decimales"), ("0.25", "decimales"),
            ("1.000", "ambiguo"), ("1,000", "ambiguo"), ("12.500", "ambiguo"),
            ("10 mL", "no es un número"), ("abc", "no es un número"), (True, "no es un número"),
            (-3, "negativa"), ("-3", "no es un número"), (3_000_000_000, "grande"),
            (float("nan"), "no es un número"),
        ]
        for valor, parte_del_motivo in casos:
            numero, motivo = parsear_cantidad(valor)
            self.assertIsNone(numero, valor)
            self.assertIn(parte_del_motivo, motivo, valor)


class PruebasMapeo(unittest.TestCase):

    def test_formato_del_excel_original(self):
        enc = ["ID Item", "Item", "Referencia", "Cantidad", "Ubicación", "Observaciones"]
        self.assertEqual(adivinar_mapeo(enc), {
            "nombre": "item", "cantidad": "cantidad", "referencia": "referencia",
            "ubicacion": "ubicacion", "observaciones": "observaciones"})
        # El ID Item (1, 2, 3...) no se importa: el sistema genera su propio id
        self.assertEqual(columnas_sin_usar(enc, adivinar_mapeo(enc)), ["ID Item"])

    def test_no_importa_el_orden_ni_como_se_escriba(self):
        a = adivinar_mapeo(["Cant.", "NOMBRE", "Código"])
        b = adivinar_mapeo(["código", "nombre", "cant"])
        self.assertEqual(a, {"cantidad": "cant", "nombre": "nombre", "referencia": "codigo"})
        self.assertEqual(a, b)

    def test_descripcion_es_el_nombre_solo_si_no_hay_otra_columna_de_nombre(self):
        self.assertEqual(adivinar_mapeo(["Descripción", "Cantidad"]),
                         {"nombre": "descripcion", "cantidad": "cantidad"})
        self.assertEqual(adivinar_mapeo(["Item", "Descripción", "Cantidad"]),
                         {"nombre": "item", "observaciones": "descripcion", "cantidad": "cantidad"})
        self.assertEqual(adivinar_mapeo(["Item", "Cantidad", "Observaciones", "Descripción"]),
                         {"nombre": "item", "cantidad": "cantidad", "observaciones": "observaciones"})

    def test_el_excel_que_exporta_la_propia_app(self):
        enc = ["ID", "Nombre", "Referencia", "Total", "Disponible", "Prestado", "Ubicación", "Observaciones"]
        mapeo = adivinar_mapeo(enc)
        self.assertEqual(mapeo["cantidad"], "total")
        self.assertEqual(columnas_sin_usar(enc, mapeo), ["ID", "Disponible", "Prestado"])

    def test_encabezado_que_contiene_la_palabra_clave(self):
        mapeo = adivinar_mapeo(["Nombre del producto", "Cantidad (und)", "Ubicación física"])
        self.assertEqual(mapeo, {"nombre": "nombre del producto", "cantidad": "cantidad und",
                                 "ubicacion": "ubicacion fisica"})

    def test_otros_campos(self):
        mapeo = adivinar_mapeo(["Reactivo", "Stock", "Unidad de medida", "Categoría", "Laboratorio"])
        self.assertEqual(mapeo, {"nombre": "reactivo", "cantidad": "stock", "unidad": "unidad de medida",
                                 "tipo": "categoria", "deposito": "laboratorio"})

    def test_detecta_el_encabezado_debajo_de_titulos(self):
        filas = [["INVENTARIO 2026"], [], ["Fecha:", "19/10"], ["Item", "Cant.", "Código"], ["Pesa", 3, "P1"]]
        self.assertEqual(detectar_fila_encabezado(filas), 4)

    def test_sin_encabezados_reconocibles_no_inventa(self):
        self.assertIsNone(detectar_fila_encabezado([["xx", "yy"], ["zz", 1]]))
        self.assertIsNone(detectar_fila_encabezado([["Item", 3]]))        # una sola coincidencia no basta

    def test_resolver_indices_funciona_con_cualquier_orden(self):
        mapeo = {"nombre": "item", "cantidad": "cant"}
        self.assertEqual(resolver_indices(["Cant.", "Item", "Otro"], mapeo), {"cantidad": 0, "nombre": 1})
        self.assertEqual(resolver_indices(["Item", "Otro", "CANT"], mapeo), {"nombre": 0, "cantidad": 2})
        self.assertEqual(resolver_indices(["Item", None, ""], mapeo), {"nombre": 0})

    def test_campos_faltantes(self):
        self.assertEqual(campos_faltantes({"nombre": "x"}), ["Cantidad"])
        self.assertEqual(campos_faltantes({"nombre": "x", "cantidad": "y"}), [])
        self.assertEqual(campos_faltantes({"nombre": "x", "cantidad": "y"}, necesita_deposito=True),
                         ["Depósito"])

    def test_un_perfil_solo_se_aplica_si_estan_todas_sus_columnas(self):
        perfiles = [
            {"id": 1, "nombre": "Física", "mapeo": {"nombre": "insumo raro", "cantidad": "n"}},
            {"id": 2, "nombre": "Química", "mapeo": {"nombre": "reactivo", "cantidad": "stock", "unidad": "um"}},
        ]
        self.assertEqual(mapeo_de_perfil(["N", "Insumo raro", "Otra"], perfiles)[0], "Física")
        self.assertEqual(mapeo_de_perfil(["Reactivo", "Stock"], perfiles), (None, {}))   # falta «um»
        nombre, mapeo = proponer_mapeo(["Reactivo", "Stock"], perfiles)                  # → adivina
        self.assertIsNone(nombre)
        self.assertEqual(mapeo, {"nombre": "reactivo", "cantidad": "stock"})


if __name__ == "__main__":
    unittest.main()
