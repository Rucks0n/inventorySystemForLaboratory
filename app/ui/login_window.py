"""
app/ui/login_window.py
-----------------------
Ventana de autenticación.
Se muestra al iniciar el sistema antes de la ventana principal.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt

from app.controllers.auth_controller import AuthController
from app.utils.logger import log


class LoginWindow(QDialog):
    """Ventana de inicio de sesión."""

    def __init__(self):
        super().__init__()
        self.usuario_autenticado = None
        self._configurar_ventana()
        self._construir_ui()

    def _configurar_ventana(self):
        self.setWindowTitle("Iniciar sesión")
        self.setFixedSize(360, 220)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

    def _construir_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(30, 30, 30, 30)

        # Título
        titulo = QLabel("Sistema de Inventario")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)

        # Campo usuario
        self.input_usuario = QLineEdit()
        self.input_usuario.setPlaceholderText("Usuario")
        layout.addWidget(self.input_usuario)

        # Campo contraseña
        self.input_contrasena = QLineEdit()
        self.input_contrasena.setPlaceholderText("Contraseña")
        self.input_contrasena.setEchoMode(QLineEdit.EchoMode.Password)
        # Permite hacer login presionando Enter
        self.input_contrasena.returnPressed.connect(self._intentar_login)
        layout.addWidget(self.input_contrasena)

        # Botón ingresar
        btn = QPushButton("Ingresar")
        btn.clicked.connect(self._intentar_login)
        layout.addWidget(btn)

        self.setLayout(layout)

    def _intentar_login(self):
        """Valida las credenciales y cierra el diálogo si son correctas."""
        usuario    = self.input_usuario.text().strip()
        contrasena = self.input_contrasena.text().strip()

        if not usuario or not contrasena:
            QMessageBox.warning(self, "Campos vacíos", "Ingresa usuario y contraseña.")
            return

        auth = AuthController()
        resultado = auth.login(usuario, contrasena)

        if resultado:
            self.usuario_autenticado = resultado
            log.info(f"Login exitoso: {usuario}")
            self.accept()   # Cierra el diálogo con código Accepted
        else:
            log.warning(f"Login fallido: {usuario}")
            QMessageBox.critical(self, "Acceso denegado", "Usuario o contraseña incorrectos.")
            self.input_contrasena.clear()
            self.input_contrasena.setFocus()