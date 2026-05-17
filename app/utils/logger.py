"""
app/utils/logger.py
-------------------
Logger centralizado del sistema.
Importa 'log' desde cualquier archivo para registrar eventos y errores.

Uso en cualquier parte del proyecto:
    from app.utils.logger import log

    log.info("Producto guardado correctamente.")
    log.warning("Stock bajo en ítem X.")
    log.error("Error al leer el archivo Excel.")
    log.debug("Valor recibido: ...")   # solo aparece en modo DEBUG
"""

import logging
import os
from config.settings import LOGS_DIR

# Asegura que la carpeta logs/ exista antes de escribir
os.makedirs(LOGS_DIR, exist_ok=True)

# ── Formato de cada línea del log ──────────────────────────────────────────────
FORMATO = "%(asctime)s  [%(levelname)-8s]  %(filename)-25s → %(message)s"
FECHA   = "%Y-%m-%d %H:%M:%S"

# ── Handlers ───────────────────────────────────────────────────────────────────
_file_handler   = logging.FileHandler(
    os.path.join(LOGS_DIR, "sistema.log"),
    encoding="utf-8"
)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(logging.Formatter(FORMATO, FECHA))

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(logging.Formatter(FORMATO, FECHA))

# ── Instancia global ───────────────────────────────────────────────────────────
log = logging.getLogger("sistema_inventario")
log.setLevel(logging.DEBUG)

# Evita duplicar handlers si el módulo se importa varias veces
if not log.handlers:
    log.addHandler(_file_handler)
    log.addHandler(_console_handler)
