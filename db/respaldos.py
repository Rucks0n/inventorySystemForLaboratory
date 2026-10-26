"""
db/respaldos.py
---------------
Copias de seguridad de la base de datos.

Se usan automáticamente antes de:
    - aplicar cambios de estructura (db/migraciones.py)
    - importar un inventario desde Excel (app/services/importador/)

Las copias quedan en  db/respaldos/  y solo se conservan las últimas 10.
Para recuperar una copia: cierra la app y reemplaza db/inventario.db por ella.
"""

import os
import sqlite3
from datetime import datetime

from db import database
from app.utils.logger import log

NOMBRE_CARPETA = "respaldos"
CONSERVAR      = 10          # cuántas copias se guardan como máximo


def carpeta_respaldos() -> str:
    """Carpeta donde se guardan las copias (junto al archivo de la BD)."""
    return os.path.join(os.path.dirname(database.DB_RUTA), NOMBRE_CARPETA)


def crear_respaldo(motivo: str) -> str | None:
    """
    Copia la base de datos actual a db/respaldos/.

    motivo — palabra corta que queda en el nombre del archivo
             (ej. "antes_de_migrar", "antes_de_importar").

    Retorna la ruta de la copia, o None si todavía no existe la base.
    """
    if not os.path.exists(database.DB_RUTA):
        return None

    os.makedirs(carpeta_respaldos(), exist_ok=True)
    marca   = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(carpeta_respaldos(), f"inventario_{marca}_{motivo}.db")
    contador = 2
    while os.path.exists(destino):                 # dos copias en el mismo segundo
        destino = os.path.join(carpeta_respaldos(), f"inventario_{marca}_{motivo}_{contador}.db")
        contador += 1

    origen = sqlite3.connect(database.DB_RUTA)
    copia  = sqlite3.connect(destino)
    try:
        origen.backup(copia)         # copia consistente aunque la app esté abierta
    finally:
        copia.close()
        origen.close()

    log.info(f"Copia de seguridad creada: {destino}")
    _borrar_antiguas()
    return destino


def _borrar_antiguas():
    """Deja solo las últimas CONSERVAR copias (el nombre empieza por la fecha)."""
    copias = sorted(
        (f for f in os.listdir(carpeta_respaldos()) if f.endswith(".db")),
        reverse=True,
    )
    for nombre in copias[CONSERVAR:]:
        try:
            os.remove(os.path.join(carpeta_respaldos(), nombre))
        except OSError as e:
            log.warning(f"No se pudo borrar la copia antigua '{nombre}': {e}")
