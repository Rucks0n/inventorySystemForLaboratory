"""
config/constants.py
-------------------
Constantes fijas del sistema.
Valores que NO cambian durante la ejecución: roles, estados, mensajes, etc.
"""

# ─── Roles de usuario ──────────────────────────────────────────────────────────
ROL_ADMIN    = "admin"
ROL_USUARIO  = "usuario"
ROL_VIEWER   = "solo_lectura"

ROLES_DISPONIBLES = [ROL_ADMIN, ROL_USUARIO, ROL_VIEWER]

# ─── Estados de productos ──────────────────────────────────────────────────────
ESTADO_ACTIVO   = "activo"
ESTADO_INACTIVO = "inactivo"
ESTADO_AGOTADO  = "agotado"

# ─── Pestañas del sistema ──────────────────────────────────────────────────────
# Aquí se registran las pestañas principales.
# Cuando agregues una pestaña nueva, solo añade la entrada aquí.
PESTANAS = [
    "Inventario",
    "Movimientos",
    "Reportes",
    "Usuarios",
    "Configuración",
]

# ─── Mensajes comunes ──────────────────────────────────────────────────────────
MSG_EXITO         = "Operación realizada con éxito."
MSG_ERROR_BD      = "Error al conectar con la base de datos."
MSG_ERROR_EXCEL   = "Error al leer el archivo Excel. Verifica el formato."
MSG_SIN_DATOS     = "No hay datos para mostrar."
MSG_CAMPO_VACIO   = "Todos los campos obligatorios deben estar llenos."