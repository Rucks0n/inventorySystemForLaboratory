"""
config/settings.py
------------------
Configuración central del sistema.
Si necesitas cambiar rutas, nombre de la BD, versión u otras
opciones globales, este es el único archivo que debes tocar.
"""

import os

# ─── Información del sistema ───────────────────────────────────────────────────
APP_NOMBRE   = "Sistema de Inventario"
APP_VERSION  = "1.0.0"
APP_ANCHO    = 1200          # Ancho inicial de la ventana en píxeles
APP_ALTO     = 700           # Alto inicial de la ventana en píxeles

# ─── Rutas base ────────────────────────────────────────────────────────────────
# BASE_DIR apunta siempre a la raíz del proyecto sin importar desde dónde se ejecute
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_DIR       = os.path.join(BASE_DIR, "db")
ASSETS_DIR   = os.path.join(BASE_DIR, "assets")
DATA_DIR     = os.path.join(BASE_DIR, "data")
LOGS_DIR     = os.path.join(BASE_DIR, "logs")

# ─── Base de datos ─────────────────────────────────────────────────────────────
DB_NOMBRE    = "inventario.db"
DB_RUTA      = os.path.join(DB_DIR, DB_NOMBRE)

# ─── Estilos ───────────────────────────────────────────────────────────────────
ESTILO_RUTA  = os.path.join(ASSETS_DIR, "styles", "theme.qss")

# ─── Excel ─────────────────────────────────────────────────────────────────────
PLANTILLA_PRODUCTOS = os.path.join(DATA_DIR, "plantilla_productos.xlsx")