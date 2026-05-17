"""
app/ui/inventario_view.py
--------------------------
Pestaña principal de inventario.
Contiene un QTabWidget interno con una pestaña por depósito.

Cada pestaña muestra:
    - Tabla de ítems del depósito
    - Buscador global
    - Botones: Agregar / Editar / Eliminar ítem

Flujo:
    InventarioView
        └── QTabWidget interno
                ├── _TabDeposito (Depósito1)
                ├── _TabDeposito (Depósito2)
                └── _TabDeposito (Depósito3)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QLineEdit, QLabel, QMessageBox,
    QDialog, QFormLayout, QSpinBox, QTextEdit,
    QComboBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui  import QFont, QColor

from app.controllers.inventario_controller import InventarioController
from app.utils.logger                       import log
from config.constants                       import COLS_INVENTARIO


class InventarioView(QWidget):
    """Vista principal de inventario con pestañas por depósito."""

    def __init__(self, usuario: dict):
        super().__init__()
        self.usuario    = usuario
        self.controller = InventarioController()
        self._construir_ui()
        self._cargar_depositos()

    # ── UI principal ───────────────────────────────────────────────────────────

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ── Barra superior: título + buscador global ───────────────────────────
        barra = QHBoxLayout()

        lbl = QLabel("Inventario")
        lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #2E5090;")

        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("🔍  Buscar en todos los depósitos...")
        self.input_buscar.setFixedWidth(320)
        self.input_buscar.setFixedHeight(34)
        self.input_buscar.setStyleSheet(self._estilo_input())
        # Búsqueda con pequeño delay para no consultar en cada tecla
        self._timer_busqueda = QTimer()
        self._timer_busqueda.setSingleShot(True)
        self._timer_busqueda.timeout.connect(self._buscar)
        self.input_buscar.textChanged.connect(
            lambda: self._timer_busqueda.start(350)
        )

        btn_limpiar = QPushButton("✕")
        btn_limpiar.setFixedSize(34, 34)
        btn_limpiar.setToolTip("Limpiar búsqueda")
        btn_limpiar.setStyleSheet(self._estilo_btn_secundario())
        btn_limpiar.clicked.connect(self._limpiar_busqueda)

        barra.addWidget(lbl)
        barra.addStretch()
        barra.addWidget(self.input_buscar)
        barra.addWidget(btn_limpiar)
        layout.addLayout(barra)

        # ── Pestañas internas por depósito ────────────────────────────────────
        self.tabs_depositos = QTabWidget()
        self.tabs_depositos.setStyleSheet(self._estilo_tabs_internos())
        layout.addWidget(self.tabs_depositos)

        # ── Barra de acciones inferior ─────────────────────────────────────────
        acciones = QHBoxLayout()

        self.btn_agregar  = QPushButton("＋  Agregar ítem")
        self.btn_editar   = QPushButton("✏  Editar ítem")
        self.btn_eliminar = QPushButton("🗑  Eliminar ítem")

        for btn in [self.btn_agregar, self.btn_editar, self.btn_eliminar]:
            btn.setFixedHeight(36)
            btn.setStyleSheet(self._estilo_btn_accion())

        self.btn_eliminar.setStyleSheet(self._estilo_btn_peligro())
        self.btn_agregar.clicked.connect(self._abrir_formulario_agregar)
        self.btn_editar.clicked.connect(self._abrir_formulario_editar)
        self.btn_eliminar.clicked.connect(self._eliminar_item)

        self.lbl_total = QLabel("")
        self.lbl_total.setStyleSheet("color: #666; font-size: 12px;")

        acciones.addWidget(self.btn_agregar)
        acciones.addWidget(self.btn_editar)
        acciones.addWidget(self.btn_eliminar)
        acciones.addStretch()
        acciones.addWidget(self.lbl_total)
        layout.addLayout(acciones)

    # ── Carga de datos ─────────────────────────────────────────────────────────

    def _cargar_depositos(self):
        """Crea una pestaña interna por cada depósito registrado en la BD."""
        self.tabs_depositos.clear()
        depositos = self.controller.obtener_depositos()

        if not depositos:
            self.tabs_depositos.addTab(QLabel("No hay depósitos registrados."), "—")
            return

        for dep in depositos:
            tab = _TabDeposito(dep, self.controller)
            self.tabs_depositos.addTab(tab, f"  {dep['nombre']}  ")

        self._actualizar_total()

    def _actualizar_total(self):
        """Muestra el total de ítems en la pestaña activa."""
        tab = self.tabs_depositos.currentWidget()
        if isinstance(tab, _TabDeposito):
            n = tab.tabla.rowCount()
            self.lbl_total.setText(f"{n} ítem(s) en este depósito")

    # ── Búsqueda ───────────────────────────────────────────────────────────────

    def _buscar(self):
        texto = self.input_buscar.text().strip()
        if not texto:
            self._limpiar_busqueda()
            return

        items = self.controller.buscar_items(texto)

        # Mostrar resultados en una pestaña temporal "Resultados"
        idx = self._indice_tab("Resultados")
        if idx >= 0:
            self.tabs_depositos.removeTab(idx)

        tab_resultado = _TabResultados(items)
        self.tabs_depositos.addTab(tab_resultado, f"🔍  Resultados ({len(items)})")
        self.tabs_depositos.setCurrentWidget(tab_resultado)

    def _limpiar_busqueda(self):
        self.input_buscar.clear()
        idx = self._indice_tab("Resultados")
        if idx >= 0:
            self.tabs_depositos.removeTab(idx)
        self.tabs_depositos.setCurrentIndex(0)

    def _indice_tab(self, texto: str) -> int:
        for i in range(self.tabs_depositos.count()):
            if texto in self.tabs_depositos.tabText(i):
                return i
        return -1

    # ── Acciones ───────────────────────────────────────────────────────────────

    def _tab_activa(self) -> "_TabDeposito | None":
        tab = self.tabs_depositos.currentWidget()
        return tab if isinstance(tab, _TabDeposito) else None

    def _item_seleccionado(self) -> dict | None:
        tab = self._tab_activa()
        if tab:
            return tab.item_seleccionado()
        return None

    def _abrir_formulario_agregar(self):
        tab = self._tab_activa()
        if not tab:
            QMessageBox.information(self, "Aviso", "Selecciona un depósito primero.")
            return

        depositos = self.controller.obtener_depositos()
        dlg = FormularioItem(depositos=depositos, deposito_actual=tab.deposito)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = self.controller.agregar_item(dlg.datos())
            if ok:
                tab.recargar()
                self._actualizar_total()
            else:
                QMessageBox.warning(self, "Error", msg)

    def _abrir_formulario_editar(self):
        item = self._item_seleccionado()
        if not item:
            QMessageBox.information(self, "Aviso", "Selecciona un ítem para editar.")
            return

        depositos = self.controller.obtener_depositos()
        dlg = FormularioItem(depositos=depositos, item_existente=item)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = self.controller.editar_item(item["id"], dlg.datos())
            if ok:
                tab = self._tab_activa()
                if tab:
                    tab.recargar()
            else:
                QMessageBox.warning(self, "Error", msg)

    def _eliminar_item(self):
        item = self._item_seleccionado()
        if not item:
            QMessageBox.information(self, "Aviso", "Selecciona un ítem para eliminar.")
            return

        confirm = QMessageBox.question(
            self, "Confirmar eliminación",
            f"¿Eliminar el ítem '{item['nombre']}'?\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            ok, msg = self.controller.eliminar_item(item["id"])
            if ok:
                tab = self._tab_activa()
                if tab:
                    tab.recargar()
                self._actualizar_total()
            else:
                QMessageBox.warning(self, "No se puede eliminar", msg)

    # ── Estilos ────────────────────────────────────────────────────────────────

    @staticmethod
    def _estilo_input():
        return """
            QLineEdit {
                border: 1px solid #CCC;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #2E5090; }
        """

    @staticmethod
    def _estilo_tabs_internos():
        return """
            QTabBar::tab {
                background: #DDE2EE;
                color: #444;
                padding: 8px 18px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #4A7ACC;
                color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected { background: #C5CCE0; }
        """

    @staticmethod
    def _estilo_btn_accion():
        return """
            QPushButton {
                background: #2E5090; color: white;
                border-radius: 4px; padding: 0 16px; font-size: 13px;
            }
            QPushButton:hover   { background: #3A63B0; }
            QPushButton:pressed { background: #1E3A6E; }
        """

    @staticmethod
    def _estilo_btn_peligro():
        return """
            QPushButton {
                background: #C0392B; color: white;
                border-radius: 4px; padding: 0 16px; font-size: 13px;
            }
            QPushButton:hover   { background: #E74C3C; }
            QPushButton:pressed { background: #922B21; }
        """

    @staticmethod
    def _estilo_btn_secundario():
        return """
            QPushButton {
                background: #EEE; color: #555;
                border-radius: 4px; border: 1px solid #CCC; font-size: 13px;
            }
            QPushButton:hover { background: #DDD; }
        """


# ─────────────────────────────────────────────────────────────────────────────
#  PESTAÑA INTERNA: tabla de un depósito
# ─────────────────────────────────────────────────────────────────────────────

class _TabDeposito(QWidget):
    """Widget interno que representa la tabla de un depósito."""

    COLUMNAS = ["ID", "Nombre", "Referencia", "Total", "Disponible", "Prestado", "Veces", "Ubicación", "Observaciones"]

    def __init__(self, deposito: dict, controller: InventarioController):
        super().__init__()
        self.deposito   = deposito
        self.controller = controller
        self._construir_ui()
        self.recargar()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 4)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setStyleSheet(self._estilo_tabla())

        # Anchos de columna
        self.tabla.setColumnWidth(0, 50)   # ID
        self.tabla.setColumnWidth(1, 220)  # Nombre
        self.tabla.setColumnWidth(2, 120)  # Referencia
        self.tabla.setColumnWidth(3, 70)   # Total
        self.tabla.setColumnWidth(4, 80)   # Disponible
        self.tabla.setColumnWidth(5, 70)   # Prestado
        self.tabla.setColumnWidth(6, 60)   # Veces
        self.tabla.setColumnWidth(7, 130)  # Ubicación

        layout.addWidget(self.tabla)

    def recargar(self):
        """Reconsulta la BD y actualiza la tabla."""
        items = self.controller.obtener_items_por_deposito(self.deposito["id"])
        self.tabla.setRowCount(0)

        for item in items:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)

            valores = [
                str(item.get("id", "")),
                item.get("nombre", ""),
                item.get("referencia", "") or "",
                str(item.get("cantidad_total", 0)),
                str(item.get("cantidad_disp", 0)),
                str(item.get("cantidad_prest", 0)),
                str(item.get("veces_prestado", 0)),
                item.get("ubicacion", "") or "",
                item.get("observaciones", "") or "",
            ]

            for col, valor in enumerate(valores):
                celda = QTableWidgetItem(valor)
                celda.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                # Colorear disponibilidad
                if col == 4:  # Disponible
                    disp = int(item.get("cantidad_disp", 0))
                    if disp == 0:
                        celda.setForeground(QColor("#C0392B"))
                    elif disp <= 2:
                        celda.setForeground(QColor("#E67E22"))
                self.tabla.setItem(fila, col, celda)

        log.debug(f"Tabla {self.deposito['nombre']}: {len(items)} ítems cargados.")

    def item_seleccionado(self) -> dict | None:
        """Retorna el dict del ítem seleccionado en la tabla, o None."""
        fila = self.tabla.currentRow()
        if fila < 0:
            return None
        item_id = int(self.tabla.item(fila, 0).text())
        return self.controller.obtener_item_por_id(item_id)

    @staticmethod
    def _estilo_tabla():
        return """
            QTableWidget {
                border: 1px solid #DDD;
                gridline-color: #EEE;
                font-size: 13px;
            }
            QTableWidget::item:selected {
                background: #2E5090;
                color: white;
            }
            QHeaderView::section {
                background: #2E5090;
                color: white;
                padding: 6px;
                font-weight: bold;
                border: none;
            }
            QTableWidget::item:alternate { background: #F5F7FC; }
        """


# ─────────────────────────────────────────────────────────────────────────────
#  PESTAÑA TEMPORAL: resultados de búsqueda
# ─────────────────────────────────────────────────────────────────────────────

class _TabResultados(QWidget):
    """Pestaña temporal que muestra resultados de búsqueda de todos los depósitos."""

    COLUMNAS = ["ID", "Depósito", "Nombre", "Referencia", "Total", "Disponible", "Prestado", "Ubicación"]

    def __init__(self, items: list[dict]):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 4)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setStyleSheet(_TabDeposito._estilo_tabla())

        self.tabla.setRowCount(0)
        for item in items:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)
            for col, valor in enumerate([
                str(item.get("id", "")),
                item.get("deposito", ""),
                item.get("nombre", ""),
                item.get("referencia", "") or "",
                str(item.get("cantidad_total", 0)),
                str(item.get("cantidad_disp", 0)),
                str(item.get("cantidad_prest", 0)),
                item.get("ubicacion", "") or "",
            ]):
                self.tabla.setItem(fila, col, QTableWidgetItem(valor))

        layout.addWidget(self.tabla)


# ─────────────────────────────────────────────────────────────────────────────
#  FORMULARIO: agregar / editar ítem
# ─────────────────────────────────────────────────────────────────────────────

class FormularioItem(QDialog):
    """
    Diálogo reutilizable para agregar o editar un ítem.
    Si se pasa item_existente, se carga con sus datos actuales.
    """

    def __init__(self, depositos: list[dict], deposito_actual: dict = None, item_existente: dict = None):
        super().__init__()
        self._depositos      = depositos
        self._deposito_actual = deposito_actual
        self._item           = item_existente
        self._modo_edicion   = item_existente is not None
        self._construir_ui()
        if self._modo_edicion:
            self._rellenar(item_existente)

    def _construir_ui(self):
        titulo = "Editar ítem" if self._modo_edicion else "Agregar ítem"
        self.setWindowTitle(titulo)
        self.setFixedWidth(420)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(10)

        # Depósito
        self.combo_deposito = QComboBox()
        for dep in self._depositos:
            self.combo_deposito.addItem(dep["nombre"], userData=dep["id"])
        if self._deposito_actual:
            idx = self.combo_deposito.findText(self._deposito_actual["nombre"])
            if idx >= 0:
                self.combo_deposito.setCurrentIndex(idx)
        if self._modo_edicion:
            self.combo_deposito.setEnabled(False)

        # Campos de texto
        self.input_nombre      = QLineEdit()
        self.input_referencia  = QLineEdit()
        self.input_ubicacion   = QLineEdit()

        # Cantidad
        self.spin_cantidad = QSpinBox()
        self.spin_cantidad.setMinimum(0)
        self.spin_cantidad.setMaximum(9999)

        # Observaciones
        self.txt_observaciones = QTextEdit()
        self.txt_observaciones.setFixedHeight(70)

        form.addRow("Depósito: *",      self.combo_deposito)
        form.addRow("Nombre: *",        self.input_nombre)
        form.addRow("Referencia:",      self.input_referencia)
        form.addRow("Cantidad:",        self.spin_cantidad)
        form.addRow("Ubicación:",       self.input_ubicacion)
        form.addRow("Observaciones:",   self.txt_observaciones)

        layout.addLayout(form)

        lbl_req = QLabel("* Campos obligatorios")
        lbl_req.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(lbl_req)

        # Botones
        btns = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        self.btn_guardar = QPushButton("Guardar")
        self.btn_guardar.setDefault(True)
        self.btn_guardar.clicked.connect(self._validar_y_aceptar)
        self.btn_guardar.setStyleSheet("""
            QPushButton {
                background: #2E5090; color: white;
                border-radius: 4px; padding: 8px 20px;
            }
            QPushButton:hover { background: #3A63B0; }
        """)
        btns.addWidget(btn_cancelar)
        btns.addWidget(self.btn_guardar)
        layout.addLayout(btns)

    def _rellenar(self, item: dict):
        self.input_nombre.setText(item.get("nombre", ""))
        self.input_referencia.setText(item.get("referencia", "") or "")
        self.spin_cantidad.setValue(int(item.get("cantidad_total", 0)))
        self.input_ubicacion.setText(item.get("ubicacion", "") or "")
        self.txt_observaciones.setPlainText(item.get("observaciones", "") or "")

    def _validar_y_aceptar(self):
        if not self.input_nombre.text().strip():
            QMessageBox.warning(self, "Campo requerido", "El nombre del ítem es obligatorio.")
            self.input_nombre.setFocus()
            return
        self.accept()

    def datos(self) -> dict:
        """Retorna los datos del formulario como diccionario."""
        return {
            "deposito_id":    self.combo_deposito.currentData(),
            "nombre":         self.input_nombre.text().strip(),
            "referencia":     self.input_referencia.text().strip(),
            "cantidad_total": self.spin_cantidad.value(),
            "ubicacion":      self.input_ubicacion.text().strip(),
            "observaciones":  self.txt_observaciones.toPlainText().strip(),
        }