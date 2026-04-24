"""
app/ui/main_window.py
----------------------
Ventana principal del sistema.
Contiene el sistema de pestañas que organiza todas las secciones.

Para agregar una pestaña nueva:
    1. Importa la vista correspondiente arriba.
    2. Crea la instancia en _construir_pestanas().
    3. Agrégala con self.tabs.addTab(vista, "Nombre").
    Eso es todo — no hay que tocar ningún otro archivo.
"""

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QStatusBar
from PyQt6.QtCore    import Qt

from config.settings   import APP_NOMBRE, APP_VERSION, APP_ANCHO, APP_ALTO

# ── Importa cada vista de pestaña ─────────────────────────────────────────────
# Cuando crees una vista nueva, agrégala aquí
from app.ui.inventario_view  import InventarioView
from app.ui.reportes_view    import ReportesView

from app.utils.logger import log


class MainWindow(QMainWindow):
    """Ventana principal del sistema."""

    def __init__(self, usuario_actual: dict):
        """
        Parámetro:
            usuario_actual: diccionario con los datos del usuario logueado.
                            Ejemplo: {"id": 1, "nombre": "Ana", "rol": "admin"}
        """
        super().__init__()
        self.usuario = usuario_actual
        self._configurar_ventana()
        self._construir_pestanas()
        self._configurar_barra_estado()
        log.info(f"Sesión iniciada — usuario: {self.usuario.get('nombre')}")

    # ── Configuración general ──────────────────────────────────────────────────

    def _configurar_ventana(self):
        self.setWindowTitle(f"{APP_NOMBRE}  v{APP_VERSION}")
        self.resize(APP_ANCHO, APP_ALTO)

    # ── Pestañas ───────────────────────────────────────────────────────────────

    def _construir_pestanas(self):
        """
        Aquí se instancia cada pestaña y se agrega al QTabWidget.
        Cada vista es un archivo independiente en app/ui/.
        """
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.setCentralWidget(self.tabs)

        # ── Agrega pestañas aquí ───────────────────────────────────────────────
        self.tabs.addTab(InventarioView(self.usuario), "📦  Inventario")
        self.tabs.addTab(ReportesView(self.usuario),   "📊  Reportes")
        # self.tabs.addTab(UsuariosView(self.usuario),  "👤  Usuarios")   ← ejemplo futuro
        # self.tabs.addTab(ConfigView(self.usuario),    "⚙️  Configuración")

    # ── Barra de estado inferior ───────────────────────────────────────────────

    def _configurar_barra_estado(self):
        barra = QStatusBar()
        nombre = self.usuario.get("nombre", "—")
        rol    = self.usuario.get("rol", "—")
        barra.showMessage(f"Usuario: {nombre}   |   Rol: {rol}   |   {APP_NOMBRE} {APP_VERSION}")
        self.setStatusBar(barra)