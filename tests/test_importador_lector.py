"""
tests/test_importador_lector.py
-------------------------------
Pruebas de la lectura de archivos: lo que suele salir mal con Excel y CSV reales.
"""

import os
import re
import tempfile
import unittest
import zipfile

from app.services.importador import lector
from app.services.importador.modelos import ErrorImportacion
from tests.ayuda_importador import crear_csv, crear_xlsx


class PruebasLector(unittest.TestCase):

    def setUp(self):
        self._carpeta = tempfile.TemporaryDirectory()
        self.carpeta = self._carpeta.name

    def tearDown(self):
        self._carpeta.cleanup()

    def ruta(self, nombre):
        return os.path.join(self.carpeta, nombre)

    # ── Excel ──────────────────────────────────────────────────────────────

    def test_lista_las_hojas_y_marca_las_ocultas(self):
        ruta = crear_xlsx(self.ruta("a.xlsx"), {"Lab A": [["x"]], "Auxiliar": [["y"]]}, ocultas=("Auxiliar",))
        self.assertEqual(lector.listar_hojas(ruta),
                         [lector.HojaInfo("Lab A", True), lector.HojaInfo("Auxiliar", False)])

    def test_salta_filas_vacias_pero_conserva_el_numero_real_de_fila(self):
        ruta = crear_xlsx(self.ruta("a.xlsx"), {"H": [
            ["Item", "Cant."],            # 1
            ["Pesa", 5],                  # 2
            [],                           # 3  (vacía)
            [None, None],                 # 4  (vacía)
            ["Sensor", 2],                # 5
        ]})
        self.assertEqual(list(lector.leer_filas(ruta, "H", 2)), [(2, ["Pesa", 5]), (5, ["Sensor", 2])])

    def test_empezar_a_leer_en_una_fila_intermedia(self):
        ruta = crear_xlsx(self.ruta("a.xlsx"), {"H": [["a"], ["b"], ["c"], ["d"]]})
        self.assertEqual([n for n, _ in lector.leer_filas(ruta, "H", 3)], [3, 4])

    def test_previa_incluye_las_filas_vacias(self):
        ruta = crear_xlsx(self.ruta("a.xlsx"), {"H": [["Título"], [], ["Item", "Cant."]]})
        self.assertEqual(lector.leer_previa(ruta, "H"), [["Título"], [], ["Item", "Cant."]])
        self.assertEqual(len(lector.leer_previa(ruta, "H", max_filas=2)), 2)

    def test_dimension_mal_declarada_no_hace_perder_filas(self):
        """Archivos hechos por otros programas pueden declarar 'A1' como tamaño; sin corregirlo
        se leería UNA sola celda y el resto del inventario se perdería sin avisar."""
        ok = crear_xlsx(self.ruta("ok.xlsx"), {"H": [["Item", "Cant."], ["Pesa", 5], ["Sensor", 2]]})
        mal = self.ruta("mal.xlsx")
        with zipfile.ZipFile(ok) as origen, zipfile.ZipFile(mal, "w") as destino:
            for parte in origen.infolist():
                datos = origen.read(parte.filename)
                if parte.filename == "xl/worksheets/sheet1.xml":
                    datos = re.sub(rb'<dimension ref="[^"]*"\s*/>', b'<dimension ref="A1"/>', datos)
                destino.writestr(parte, datos)
        self.assertEqual(len(list(lector.leer_filas(mal, "H", 1))), 3)

    def test_lee_el_valor_calculado_de_las_formulas_o_none_si_nunca_se_calcularon(self):
        # openpyxl guarda la fórmula sin valor calculado: se lee como vacío (no como "=A1+1")
        ruta = crear_xlsx(self.ruta("f.xlsx"), {"H": [["Item", "Cant."], ["Pesa", "=1+1"]]})
        self.assertEqual(list(lector.leer_filas(ruta, "H", 2)), [(2, ["Pesa", None])])

    # ── CSV ────────────────────────────────────────────────────────────────

    def test_csv_de_excel_en_espanol(self):
        ruta = crear_csv(self.ruta("es.csv"),
                         [["Nombre", "Cantidad", "Ubicación"], ["Ácido nítrico", 2, "Estante ñ"], ["Guantes", 10, ""]],
                         separador=";", codificacion="cp1252")
        self.assertEqual(list(lector.leer_filas(ruta, "es", 2)),
                         [(2, ["Ácido nítrico", "2", "Estante ñ"]), (3, ["Guantes", "10", None])])

    def test_csv_utf8_con_bom_y_comas_dentro_de_comillas(self):
        ruta = crear_csv(self.ruta("bom.csv"), [["Nombre", "Cantidad"], ["Cable, USB", 4]],
                         separador=",", codificacion="utf-8-sig")
        self.assertEqual(list(lector.leer_filas(ruta, "bom", 1)),
                         [(1, ["Nombre", "Cantidad"]), (2, ["Cable, USB", "4"])])

    def test_un_csv_cuenta_como_una_sola_hoja(self):
        ruta = crear_csv(self.ruta("inventario_lab.csv"), [["a"]])
        self.assertEqual(lector.listar_hojas(ruta), [lector.HojaInfo("inventario_lab", True)])

    # ── Errores que se le explican al usuario ──────────────────────────────

    def test_mensajes_claros_para_archivos_que_no_sirven(self):
        casos = {
            "viejo.xls": ("x", ".xlsx"),                  # se explica cómo convertirlo
            "notas.txt": ("x", "Formato no aceptado"),
            "roto.xlsx": ("esto no es un zip", "no parece un Excel"),
        }
        for nombre, (contenido, parte_del_mensaje) in casos.items():
            with open(self.ruta(nombre), "w") as f:
                f.write(contenido)
            with self.assertRaises(ErrorImportacion) as ctx:
                lector.listar_hojas(self.ruta(nombre))
            self.assertIn(parte_del_mensaje, str(ctx.exception), nombre)

    def test_archivo_inexistente_u_hoja_inexistente(self):
        with self.assertRaises(ErrorImportacion):
            lector.listar_hojas(self.ruta("no_existe.xlsx"))
        ruta = crear_xlsx(self.ruta("a.xlsx"), {"H": [["x"]]})
        with self.assertRaises(ErrorImportacion):
            list(lector.leer_filas(ruta, "Otra", 1))


if __name__ == "__main__":
    unittest.main()
