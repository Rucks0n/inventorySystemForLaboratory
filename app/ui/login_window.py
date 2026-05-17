"""
app/ui/login_window.py
-----------------------
Ventana de inicio de sesión.
Se muestra al arrancar el sistema antes de la ventana principal.

Después de un login exitoso, el atributo 'usuario_autenticado' contiene
el dict del usuario: {"id": 1, "nombre": "Admin", "rol": "admin", ...}
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui  import QFont, QKeyEvent

from app.controllers.auth_controller import AuthController
from app.utils.logger                 import log
from config.settings                  import APP_NOMBRE, APP_VERSION


class LoginWindow(QDialog):
    """Ventana modal de inicio de sesión."""

    def __init__(self):
        super().__init__()
        self.usuario_autenticado = None
        self._auth = AuthController()
        self._configurar_ventana()
        self._construir_ui()

    # ── Configuración ──────────────────────────────────────────────────────────

    def _configurar_ventana(self):
        self.setWindowTitle("Iniciar sesión")
        self.setFixedSize(400, 300)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Encabezado ─────────────────────────────────────────────────────────
        encabezado = QFrame()
        encabezado.setFixedHeight(90)
        encabezado.setStyleSheet("background-color: #2E5090;")
        enc_layout = QVBoxLayout(encabezado)
        enc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_titulo = QLabel(APP_NOMBRE)
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_titulo.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        lbl_titulo.setStyleSheet("color: white;")

        lbl_version = QLabel(f"v{APP_VERSION}")
        lbl_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_version.setStyleSheet("color: #A0B8D8; font-size: 11px;")

        enc_layout.addWidget(lbl_titulo)
        enc_layout.addWidget(lbl_version)

        # ── Formulario ─────────────────────────────────────────────────────────
        form = QFrame()
        form.setStyleSheet("background-color: white;")
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(40, 30, 40, 30)
        form_layout.setSpacing(12)

        # Campo usuario / código
        self.input_codigo = QLineEdit()
        self.input_codigo.setPlaceholderText("Usuario o código")
        self.input_codigo.setFixedHeight(38)
        self.input_codigo.setStyleSheet(self._estilo_input())

        # Campo contraseña
        self.input_contrasena = QLineEdit()
        self.input_contrasena.setPlaceholderText("Contraseña")
        self.input_contrasena.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_contrasena.setFixedHeight(38)
        self.input_contrasena.setStyleSheet(self._estilo_input())
        self.input_contrasena.returnPressed.connect(self._intentar_login)

        # Mensaje de error (oculto por defecto)
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #C0392B; font-size: 11px;")
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_error.setVisible(False)

        # Botón ingresar
        self.btn_ingresar = QPushButton("Ingresar")
        self.btn_ingresar.setFixedHeight(40)
        self.btn_ingresar.setStyleSheet(self._estilo_boton())
        self.btn_ingresar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ingresar.clicked.connect(self._intentar_login)

        form_layout.addWidget(QLabel("Código:"))
        form_layout.addWidget(self.input_codigo)
        form_layout.addWidget(QLabel("Contraseña:"))
        form_layout.addWidget(self.input_contrasena)
        form_layout.addWidget(self.lbl_error)
        form_layout.addSpacing(4)
        form_layout.addWidget(self.btn_ingresar)

        layout.addWidget(encabezado)
        layout.addWidget(form)

        self.input_codigo.setFocus()

    # ── Lógica de login ────────────────────────────────────────────────────────

    def _intentar_login(self):
        """Valida credenciales y cierra el diálogo si son correctas."""
        codigo     = self.input_codigo.text().strip()
        contrasena = self.input_contrasena.text().strip()

        if not codigo or not contrasena:
            self._mostrar_error("Ingresa tu código y contraseña.")
            return

        self.btn_ingresar.setEnabled(False)
        self.btn_ingresar.setText("Verificando...")

        resultado = self._auth.login(codigo, contrasena)

        self.btn_ingresar.setEnabled(True)
        self.btn_ingresar.setText("Ingresar")

        if resultado:
            self.usuario_autenticado = resultado
            self.accept()
        else:
            self._mostrar_error("Código o contraseña incorrectos.")
            self.input_contrasena.clear()
            self.input_contrasena.setFocus()

    def _mostrar_error(self, mensaje: str):
        self.lbl_error.setText(mensaje)
        self.lbl_error.setVisible(True)

    # ── Estilos ────────────────────────────────────────────────────────────────

    @staticmethod
    def _estilo_input() -> str:
        return """
            QLineEdit {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #2E5090;
            }
        """

    @staticmethod
    def _estilo_boton() -> str:
        return """
            QPushButton {
                background-color: #2E5090;
                color: white;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover   { background-color: #3A63B0; }
            QPushButton:pressed { background-color: #1E3A6E; }
            QPushButton:disabled{ background-color: #AAAAAA; }
        """