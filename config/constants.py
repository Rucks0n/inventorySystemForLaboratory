"""
config/constants.py
-------------------
Constantes fijas del sistema.
Valores que NO cambian durante la ejecución: roles, estados, mensajes, nombres de hojas Excel, etc.
"""

# ── Roles de usuario ───────────────────────────────────────────────────────────
ROL_ADMIN       = "admin"
ROL_USUARIO     = "usuario"
ROL_SOLO_LECT   = "solo_lectura"
ROLES_VALIDOS   = [ROL_ADMIN, ROL_USUARIO, ROL_SOLO_LECT]

# ── Estados de préstamo ────────────────────────────────────────────────────────
PRESTAMO_ACTIVO   = "activo"
PRESTAMO_DEVUELTO = "devuelto"
PRESTAMO_VENCIDO  = "vencido"

# ── Tipos de movimiento (igual que en el Excel original) ──────────────────────
MOV_SALIDA     = "Salida"
MOV_DEVOLUCION = "Devolución"
MOV_ENTRADA    = "Entrada"

# ── Comportamiento de los tipos de ítem ───────────────────────────────────────
# Cada tipo (Herramienta, Consumible, ...) se comporta de una de estas dos formas
COMP_PRESTA  = "presta"      # se presta y se devuelve
COMP_CONSUME = "consume"     # se gasta y se descuenta
COMPORTAMIENTOS_VALIDOS = [COMP_PRESTA, COMP_CONSUME]

# ── Importador de inventario (Excel / CSV) ────────────────────────────────────
# Cómo se reparten los ítems del archivo entre los depósitos
IMP_DEPOSITO_POR_HOJA    = "hojas"      # cada hoja del Excel es un depósito
IMP_DEPOSITO_POR_COLUMNA = "columna"    # una columna del Excel dice el depósito
IMP_DEPOSITO_UNICO       = "unico"      # todo el archivo va a un solo depósito
# Qué hacer con los ítems que ya existen en la base
IMP_DUP_OMITIR     = "omitir"           # se dejan como están (lo más seguro)
IMP_DUP_ACTUALIZAR = "actualizar"       # se actualizan con los datos del archivo
# Gravedad de los problemas encontrados en el archivo
IMP_ERROR = "error"                     # la fila NO se importa
IMP_AVISO = "aviso"                     # la fila se importa, pero conviene revisarla

# ── Hoja de docentes del Excel inventario.xlsx (importación histórica) ────────
# Si el Excel cambia de nombre de hoja, solo se actualiza aquí
HOJA_DOCENTES  = "Docente"

# ── Hojas del Excel gestion.xlsx ──────────────────────────────────────────────
HOJA_INVENTARIO  = "Inventario"
HOJA_PRESTAMOS   = "Prestamos"
HOJA_DEVOLUCIONES = "Devoluciones"
HOJA_MOVIMIENTOS = "Movimientos"

# ── Pestañas principales de la ventana ────────────────────────────────────────
# Agregar aquí cuando se cree una pestaña nueva
PESTANA_INVENTARIO  = "Inventario"
PESTANA_PRESTAMOS   = "Préstamos"
PESTANA_DOCENTES    = "Docentes"
PESTANA_USUARIOS    = "Usuarios"
PESTANA_REPORTES    = "Reportes"

# ── Columnas visibles en la tabla de inventario ───────────────────────────────
COLS_INVENTARIO = ["ID", "Nombre", "Referencia", "Total", "Disponible", "Prestado", "Ubicación", "Observaciones"]

# ── Columnas visibles en la tabla de préstamos activos ────────────────────────
COLS_PRESTAMOS  = ["ID", "Ítem", "Referencia", "Cant.", "Usuario", "Código", "Docente", "Motivo", "Fecha", "Límite"]

# ── Mensajes de interfaz ───────────────────────────────────────────────────────
MSG_EXITO         = "Operación realizada con éxito."
MSG_ERROR_BD      = "Error al conectar con la base de datos."
MSG_ERROR_EXCEL   = "Error al leer el archivo Excel. Verifica el formato."
MSG_SIN_DATOS     = "No hay datos para mostrar."
MSG_CAMPO_VACIO   = "Todos los campos obligatorios deben estar llenos."
MSG_STOCK_INSUF   = "Stock insuficiente para realizar el préstamo."
MSG_CONFIRM_ELIM  = "¿Estás seguro de que deseas eliminar este registro?"
