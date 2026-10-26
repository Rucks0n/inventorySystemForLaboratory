"""
app/ui/importar/dialogo.py
--------------------------
La ventana del asistente de importación. Solo se ocupa de la navegación
(Atrás / Siguiente / Cancelar); cada pantalla vive en su propio archivo paso_*.py.

Para agregar, quitar o reordenar pasos, edita la lista `self.pasos`.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout

from app.ui.importar.base import ESTILO_PRIMARIO, ESTILO_SECUNDARIO, EstadoAsistente
from app.ui.importar.paso_archivo import PasoArchivo
from app.ui.importar.paso_columnas import PasoColumnas
from app.ui.importar.paso_destino import PasoDestino
from app.ui.importar.paso_resultado import PasoResultado
from app.ui.importar.paso_revision import PasoRevision


class ImportarDialog(QDialog):
    """Asistente para importar un inventario desde Excel o CSV."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Importar inventario")
        self.setMinimumSize(900, 680)
        self.resize(1000, 780)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self.estado = EstadoAsistente()
        self.pasos = [PasoArchivo(self.estado), PasoColumnas(self.estado), PasoDestino(self.estado),
                      PasoRevision(self.estado), PasoResultado(self.estado)]
        self._indice = 0
        self._construir_ui()
        self._ir_a(0)

    @property
    def hubo_cambios(self) -> bool:
        """True si se guardó algo en el inventario (para que la pantalla se recargue)."""
        r = self.estado.resultado
        return bool(r and (r.creados or r.actualizados or r.depositos_creados))

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(18, 14, 18, 14)
        raiz.setSpacing(10)

        self.lbl_titulo = QLabel("")
        self.lbl_titulo.setStyleSheet("color:#2E5090;font-size:17px;font-weight:bold;")
        self.lbl_progreso = QLabel("")
        self.lbl_progreso.setStyleSheet("color:#777;")
        cabecera = QHBoxLayout()
        cabecera.addWidget(self.lbl_titulo)
        cabecera.addStretch()
        cabecera.addWidget(self.lbl_progreso)
        raiz.addLayout(cabecera)

        self.pila = QStackedWidget()
        for paso in self.pasos:
            self.pila.addWidget(paso)
            paso.cambio.connect(self._refrescar_botones)
        raiz.addWidget(self.pila, 1)

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_atras = QPushButton("‹  Atrás")
        self.btn_siguiente = QPushButton("Siguiente  ›")
        for boton, estilo in ((self.btn_cancelar, ESTILO_SECUNDARIO), (self.btn_atras, ESTILO_SECUNDARIO),
                              (self.btn_siguiente, ESTILO_PRIMARIO)):
            boton.setFixedHeight(36)
            boton.setStyleSheet(estilo)
        self.btn_cancelar.clicked.connect(self._cerrar)
        self.btn_atras.clicked.connect(self._atras)
        self.btn_siguiente.clicked.connect(self._siguiente)

        pie = QHBoxLayout()
        pie.addWidget(self.btn_cancelar)
        pie.addStretch()
        pie.addWidget(self.btn_atras)
        pie.addWidget(self.btn_siguiente)
        raiz.addLayout(pie)

    def _refrescar_botones(self):
        paso = self.pasos[self._indice]
        self.btn_atras.setVisible(self._indice > 0 and (paso.puede_volver or not paso.es_ultimo))
        self.btn_atras.setEnabled(paso.puede_volver)
        self.btn_siguiente.setVisible(not paso.es_ultimo)
        self.btn_siguiente.setText(paso.texto_siguiente)
        self.btn_siguiente.setEnabled(paso.puede_seguir)
        self.btn_cancelar.setText("Cerrar" if paso.terminado else "Cancelar")

    # ── Navegación ─────────────────────────────────────────────────────────────

    def _ir_a(self, indice: int):
        self._indice = indice
        paso = self.pasos[indice]
        self.pila.setCurrentIndex(indice)
        self.lbl_titulo.setText(paso.titulo)
        self.lbl_progreso.setText(f"Paso {indice + 1} de {len(self.pasos)}")
        paso.al_entrar()
        self._refrescar_botones()

    def _siguiente(self):
        paso = self.pasos[self._indice]
        if paso.validar():
            paso.al_salir()
            self._ir_a(self._indice + 1)

    def _atras(self):
        self.pasos[self._indice].al_salir()
        self._ir_a(self._indice - 1)

    # ── Cerrar ─────────────────────────────────────────────────────────────────

    def _cerrar(self):
        if self.pasos[self._indice].terminado:
            self.accept()
        else:
            self.reject()

    def reject(self):
        """Cerrar con «Cancelar», Esc o la X: se detiene lo que esté corriendo (sin dejar nada a medias)."""
        if not self.pasos[self._indice].confirmar_cierre():
            return
        for paso in self.pasos:
            paso.al_salir()
        super().reject()
