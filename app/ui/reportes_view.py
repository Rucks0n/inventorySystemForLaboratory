"""
app/ui/reportes_view.py
------------------------
Pestaña de reportes y dashboards.
Aquí irán gráficas, resúmenes y exportaciones.

Por ahora es un placeholder — se construye en la siguiente etapa.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore    import Qt


class ReportesView(QWidget):
    """Vista principal de la pestaña Reportes."""

    def __init__(self, usuario: dict):
        super().__init__()
        self.usuario = usuario
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout()

        label = QLabel("📊  Módulo de Reportes\n\nEn construcción...")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        self.setLayout(layout)