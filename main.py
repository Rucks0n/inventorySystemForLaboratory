"""
main.py
--------
Punto de entrada del sistema. Solo orquesta — no contiene lógica de negocio.

Orden de arranque:
    1. Ejecuta la migración (crea tablas si no existen — seguro de repetir)
    2. Crea el usuario admin por defecto en la primera ejecución
    3. Muestra la pantalla de login
    4. Si el login es exitoso, abre la ventana principal con pestañas
"""

import sys
from PyQt6.QtWidgets import QApplication, QMessageBox

from config.settings import APP_NOMBRE

# ── Migraciones ────────────────────────────────────────────────────────────────
from db.migrations.migration_001 import ejecutar as migrar

# ── Auth ───────────────────────────────────────────────────────────────────────
from app.controllers.auth_controller import AuthController

# ── Ventanas ───────────────────────────────────────────────────────────────────
from app.ui.login_window import LoginWindow
from app.ui.main_window  import MainWindow

from app.utils.logger import log


def inicializar():
    """Prepara la BD y datos iniciales. Seguro de ejecutar en cada arranque."""
    try:
        migrar()
    except Exception as e:
        log.error(f"Error en migración: {e}")
        QMessageBox.critical(
            None,
            "Error de inicialización",
            f"No se pudo inicializar la base de datos:\n{e}"
        )
        sys.exit(1)

    # Crear admin por defecto solo si no hay usuarios con contraseña
    auth = AuthController()
    auth.crear_usuario_sistema(
        nombre     = "Administrador",
        codigo     = "admin",
        contrasena = "admin123",
        rol        = "admin",
    )
    # ⚠ Cambiar estas credenciales después del primer ingreso


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NOMBRE)

    # Cargar hoja de estilos Qt si existe
    try:
        from config.settings import ESTILO_RUTA
        import os
        if os.path.exists(ESTILO_RUTA):
            with open(ESTILO_RUTA, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
    except Exception as e:
        log.warning(f"No se pudo cargar el estilo: {e}")

    # 1. Inicializar
    inicializar()
    log.info("Sistema iniciado.")

    # 2. Login
    login = LoginWindow()
    if login.exec() != LoginWindow.DialogCode.Accepted:
        log.info("Login cancelado. Cerrando.")
        sys.exit(0)

    # 3. Ventana principal
    ventana = MainWindow(usuario_actual=login.usuario_autenticado)
    ventana.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
