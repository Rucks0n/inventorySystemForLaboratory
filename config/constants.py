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

# ── Hojas del Excel inventario.xlsx ───────────────────────────────────────────
# Si el Excel cambia de nombre de hoja, solo se actualiza aquí
HOJA_DEPOSITO1 = "Depósito1"
HOJA_DEPOSITO2 = "Depósito2"
HOJA_DEPOSITO3 = "Depósito3"
HOJA_DOCENTES  = "Docente"
HOJAS_DEPOSITOS = [HOJA_DEPOSITO1, HOJA_DEPOSITO2, HOJA_DEPOSITO3]

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
