"""
Punto de entrada del sistema.
Este archivo solo orquesta — no contiene lógica de negocio.

Orden de arranque:
    1. Ejecuta las migraciones (crea tablas si no existen)
    2. Crea el usuario admin por defecto en la primera ejecución
    3. Muestra la pantalla de login
    4. Si el login es exitoso, abre la ventana principal
"""

import sys
from PyQt6.QtWidgets import QApplication

# ── Migraciones ────────────────────────────────────────────────────────────────
from db.migrations.001_initial import ejecutar as migrar

# ── Autenticación ──────────────────────────────────────────────────────────────
from app.controllers.auth_controller import AuthController

# ── Ventanas ───────────────────────────────────────────────────────────────────
from app.ui.login_window import LoginWindow
from app.ui.main_window  import MainWindow

from app.utils.logger import log


def inicializar_sistema():
    """Prepara la BD y datos iniciales en la primera ejecución."""
    migrar()

    auth = AuthController()
    # Crea un usuario admin por defecto si la BD está vacía
    # ⚠️ Cambia estas credenciales antes de entregar el sistema
    auth.crear_usuario_admin(
        nombre     = "Administrador",
        usuario    = "admin",
        contrasena = "admin123"
    )


def main():
    app = QApplication(sys.argv)

    # 1. Preparar sistema
    inicializar_sistema()
    log.info("Sistema iniciado.")

    # 2. Mostrar login
    login = LoginWindow()
    if login.exec() != LoginWindow.DialogCode.Accepted:
        # El usuario cerró la ventana de login sin autenticarse
        log.info("Login cancelado. Cerrando sistema.")
        sys.exit(0)

    # 3. Abrir ventana principal con el usuario autenticado
    ventana = MainWindow(usuario_actual=login.usuario_autenticado)
    ventana.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()