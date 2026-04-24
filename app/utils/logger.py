"""
app/utils/logger.py
-------------------
Configuración del sistema de logs.
Importa 'log' desde cualquier archivo para registrar eventos y errores.

Uso en cualquier parte del proyecto:
    from app.utils.logger import log

    log.info("Producto guardado correctamente.")
    log.warning("Stock bajo en producto X.")
    log.error("Error al leer el archivo Excel.")
"""

import logging
import os
from config.settings import LOGS_DIR

# Asegura que la carpeta logs/ exista
os.makedirs(LOGS_DIR, exist_ok=True)

# Formato de cada línea del log
FORMATO = "%(asctime)s  [%(levelname)s]  %(filename)s → %(message)s"
FECHA   = "%Y-%m-%d %H:%M:%S"

# Configuración general
logging.basicConfig(
    level=logging.INFO,
    format=FORMATO,
    datefmt=FECHA,
    handlers=[
        # Guarda los logs en archivo
        logging.FileHandler(
            os.path.join(LOGS_DIR, "sistema.log"),
            encoding="utf-8"
        ),
        # También muestra los logs en la consola
        logging.StreamHandler()
    ]
)

# Instancia global lista para importar
log = logging.getLogger("sistema_inventario")