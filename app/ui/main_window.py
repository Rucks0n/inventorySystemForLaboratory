"""
app/ui/main_window.py
----------------------
Ventana principal del sistema.
Contiene el QTabWidget que organiza todas las secciones.

Para agregar una pestaña nueva:
    1. Crea la vista en app/ui/nombre_view.py
    2. Importa la clase aquí abajo
    3. Agrega una línea en _construir_pestanas():
           self.tabs.addTab(NombreView(self.usuario), "Nombre")
    Eso es todo — ningún otro archivo se toca.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar,
    QLabel, QWidget, QHBoxLayout, QPushButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui  import QFont

from config.settings   import APP_NOMBRE, APP_VERSION, APP_ANCHO, APP_ALTO

# ── Importa cada vista ────────────────────────────────────────────────────────
from app.ui.inventario_view  import InventarioView
from app.ui.prestamos_view   import PrestamosView
from app.ui.docentes_view    import DocentesView

from app.utils.logger import log


class MainWindow(QMainWindow):
    """Ventana principal con sistema de pestañas."""

    def __init__(self, usuario_actual: dict):
        """
        Parámetro:
            usuario_actual: dict con datos del usuario logueado.
                            Ejemplo: {"id":1, "nombre":"Ana", "rol":"admin"}
        """
        super().__init__()
        self.usuario = usuario_actual
        self._configurar_ventana()
        self._construir_pestanas()
        self._configurar_barra_estado()
        log.info(f"Ventana principal abierta — usuario: {self.usuario.get('nombre')}")

    # ── Configuración general ──────────────────────────────────────────────────

    def _configurar_ventana(self):
        self.setWindowTitle(f"{APP_NOMBRE}  —  v{APP_VERSION}")
        self.resize(APP_ANCHO, APP_ALTO)
        self.setMinimumSize(900, 600)

    # ── Pestañas ───────────────────────────────────────────────────────────────

    def _construir_pestanas(self):
        """
        Instancia cada vista y la agrega al QTabWidget.
        Cada vista es un archivo independiente en app/ui/.
        """
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet(self._estilo_tabs())
        self.setCentralWidget(self.tabs)

        # ── Agregar pestañas aquí ──────────────────────────────────────────────
        self.tabs.addTab(InventarioView(self.usuario),  "📦  Inventario")
        self.tabs.addTab(PrestamosView(self.usuario),   "🔄  Préstamos")
        self.tabs.addTab(DocentesView(self.usuario),    "👤  Docentes / Usuarios")
        # self.tabs.addTab(ReportesView(self.usuario),  "📊  Reportes")   ← próximo
        # self.tabs.addTab(ConfigView(self.usuario),    "⚙️  Configuración")

    # ── Barra de estado ────────────────────────────────────────────────────────

    def _configurar_barra_estado(self):
        barra = QStatusBar()
        nombre = self.usuario.get("nombre", "—")
        rol    = self.usuario.get("rol", "—")
        barra.showMessage(
            f"Usuario: {nombre}   |   Rol: {rol}   |   {APP_NOMBRE} {APP_VERSION}"
        )
        self.setStatusBar(barra)

    # ── Estilos ────────────────────────────────────────────────────────────────

    @staticmethod
    def _estilo_tabs() -> str:
        return """
            QTabWidget::pane {
                border: none;
                background: #F5F6FA;
            }
            QTabBar::tab {
                background: #E0E4EE;
                color: #555;
                padding: 10px 22px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background: #2E5090;
                color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background: #C8CFDF;
            }
        """