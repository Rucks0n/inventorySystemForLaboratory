"""
app/services/excel_service.py
------------------------------
Manejo de archivos Excel (.xlsx).
Permite importar productos desde Excel y exportar datos a Excel.

Dependencia: pip install openpyxl
"""

import os
import openpyxl
from app.utils.logger import log


# ─── Importar desde Excel ──────────────────────────────────────────────────────

def leer_productos_excel(ruta_archivo: str) -> list[dict]:
    """
    Lee un archivo Excel y retorna una lista de productos.

    El Excel debe tener estos encabezados en la fila 1:
        codigo | nombre | categoria | cantidad | precio

    Retorna:
        Lista de diccionarios con los datos de cada fila.
        Ejemplo: [{"codigo": "P001", "nombre": "Silla", ...}, ...]
    """
    productos = []

    if not os.path.exists(ruta_archivo):
        log.error(f"Archivo no encontrado: {ruta_archivo}")
        return productos

    try:
        wb = openpyxl.load_workbook(ruta_archivo, data_only=True)
        ws = wb.active

        # La primera fila son los encabezados — se salta
        encabezados = [str(c.value).strip().lower() for c in ws[1]]

        for fila in ws.iter_rows(min_row=2, values_only=True):
            # Salta filas completamente vacías
            if all(v is None for v in fila):
                continue

            producto = dict(zip(encabezados, fila))
            productos.append(producto)

        log.info(f"Excel leído: {len(productos)} productos encontrados en {ruta_archivo}")

    except Exception as e:
        log.error(f"Error leyendo Excel {ruta_archivo}: {e}")

    return productos


# ─── Exportar a Excel ──────────────────────────────────────────────────────────

def exportar_productos_excel(productos: list[dict], ruta_destino: str) -> bool:
    """
    Exporta una lista de productos a un archivo Excel.

    Parámetros:
        productos:     Lista de diccionarios con los datos.
        ruta_destino:  Ruta donde se guardará el archivo .xlsx

    Retorna:
        True si se guardó correctamente, False si hubo error.
    """
    if not productos:
        log.warning("No hay productos para exportar.")
        return False

    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Productos"

        # Encabezados desde las claves del primer diccionario
        encabezados = list(productos[0].keys())
        ws.append(encabezados)

        # Filas de datos
        for p in productos:
            ws.append(list(p.values()))

        # Ajusta el ancho de columnas automáticamente
        for col in ws.columns:
            max_len = max(len(str(c.value or "")) for c in col)
            ws.column_dimensions[col[0].column_letter].width = max_len + 4

        os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
        wb.save(ruta_destino)
        log.info(f"Excel exportado correctamente: {ruta_destino}")
        return True

    except Exception as e:
        log.error(f"Error exportando Excel: {e}")
        return False