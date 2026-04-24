"""
app/ui/inventario_view.py
--------------------------
Pestaña de gestión de inventario.
Aquí irá la tabla de productos, botones de agregar/editar/eliminar
y la opción de importar desde Excel.

Por ahora es un placeholder — se construye en la siguiente etapa.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore    import Qt


class InventarioView(QWidget):
    """Vista principal de la pestaña Inventario."""

    def __init__(self, usuario: dict):
        super().__init__()
        self.usuario = usuario
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout()

        # Placeholder — se reemplazará con la tabla real
        label = QLabel("📦  Módulo de Inventario\n\nEn construcción...")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        self.setLayout(layout)