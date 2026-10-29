"""
app/ui/inventario_view.py
--------------------------
Vista de inventario con pestañas dinámicas por depósito.

Si el usuario es admin ve además el panel de gestión de depósitos
donde puede crear, editar y eliminar espacios con cualquier nombre.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QMessageBox,
    QDialog, QFormLayout, QSpinBox, QTextEdit,
    QComboBox, QAbstractItemView, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui  import QFont, QColor

from app.controllers.inventario_controller import InventarioController, DepositosController
from app.ui.importar                        import ImportarDialog
from app.utils.logger                       import log
from config.constants                       import ROL_ADMIN


class InventarioView(QWidget):
    """Vista principal de inventario."""

    def __init__(self, usuario: dict):
        super().__init__()
        self.usuario     = usuario
        self.es_admin    = usuario.get("rol") == ROL_ADMIN
        self.ctrl_inv    = InventarioController()
        self.ctrl_dep    = DepositosController()
        self._construir_ui()
        self._cargar_depositos()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Barra superior
        barra = QHBoxLayout()
        lbl = QLabel("Inventario")
        lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #2E5090;")

        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("🔍  Buscar en todos los depósitos...")
        self.input_buscar.setFixedWidth(320)
        self.input_buscar.setFixedHeight(34)
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._buscar)
        self.input_buscar.textChanged.connect(lambda: self._timer.start(350))

        btn_limpiar = QPushButton("✕")
        btn_limpiar.setFixedSize(34, 34)
        btn_limpiar.setToolTip("Limpiar búsqueda")
        btn_limpiar.clicked.connect(self._limpiar_busqueda)

        barra.addWidget(lbl)
        barra.addStretch()
        barra.addWidget(self.input_buscar)
        barra.addWidget(btn_limpiar)

        # Depósitos e importación (solo admin)
        if self.es_admin:
            barra.addSpacing(16)
            btn_depositos = QPushButton("🗂  Gestionar depósitos")
            btn_depositos.setFixedHeight(34)
            btn_depositos.setStyleSheet(self._btn_admin())
            btn_depositos.clicked.connect(self._gestionar_depositos)
            barra.addWidget(btn_depositos)

            btn_importar = QPushButton("📥  Importar inventario")
            btn_importar.setFixedHeight(34)
            btn_importar.setStyleSheet(self._btn_admin())
            btn_importar.clicked.connect(self._importar_inventario)
            barra.addWidget(btn_importar)

        layout.addLayout(barra)

        # Pestañas por depósito
        self.tabs_depositos = QTabWidget()
        self.tabs_depositos.setStyleSheet(self._estilo_tabs())
        self.tabs_depositos.currentChanged.connect(self._actualizar_total)
        layout.addWidget(self.tabs_depositos)

        # Acciones de ítems
        acciones = QHBoxLayout()
        self.btn_agregar  = QPushButton("＋  Agregar ítem")
        self.btn_editar   = QPushButton("✏  Editar ítem")
        self.btn_eliminar = QPushButton("🗑  Eliminar ítem")
        self.lbl_total    = QLabel("")

        for btn in [self.btn_agregar, self.btn_editar, self.btn_eliminar]:
            btn.setFixedHeight(36)

        self.btn_agregar.setStyleSheet(self._btn_primario())
        self.btn_editar.setStyleSheet(self._btn_secundario())
        self.btn_eliminar.setStyleSheet(self._btn_peligro())
        self.lbl_total.setStyleSheet("color: #666; font-size: 12px;")

        self.btn_agregar.clicked.connect(self._agregar_item)
        self.btn_editar.clicked.connect(self._editar_item)
        self.btn_eliminar.clicked.connect(self._eliminar_item)

        # Solo admin puede agregar/editar/eliminar ítems
        if not self.es_admin:
            self.btn_agregar.setVisible(False)
            self.btn_editar.setVisible(False)
            self.btn_eliminar.setVisible(False)

        acciones.addWidget(self.btn_agregar)
        acciones.addWidget(self.btn_editar)
        acciones.addWidget(self.btn_eliminar)
        acciones.addStretch()
        acciones.addWidget(self.lbl_total)
        layout.addLayout(acciones)

    # ── Depósitos ──────────────────────────────────────────────────────────────

    def _cargar_depositos(self):
        """Recrea las pestañas internas según los depósitos en BD."""
        self.tabs_depositos.clear()
        depositos = self.ctrl_dep.obtener_todos()

        if not depositos:
            aviso = QLabel("No hay depósitos creados.\nUsa '🗂 Gestionar depósitos' para crear uno.")
            aviso.setAlignment(Qt.AlignmentFlag.AlignCenter)
            aviso.setStyleSheet("color: #888; font-size: 14px;")
            self.tabs_depositos.addTab(aviso, "—")
            return

        for dep in depositos:
            tab = _TabDeposito(dep, self.ctrl_inv)
            self.tabs_depositos.addTab(tab, f"  {dep['nombre']}  ")

        self._actualizar_total()

    def _gestionar_depositos(self):
        """Abre el diálogo de gestión de depósitos (solo admin)."""
        dlg = GestionDepositos(self.ctrl_dep, parent=self)
        dlg.exec()
        # Recargar pestañas al cerrar por si hubo cambios
        self._cargar_depositos()

    def actualizar(self):
        """
        Vuelve a leer las cantidades (MainWindow lo llama al entrar a esta pestaña, por
        ejemplo después de registrar un préstamo en la pestaña de Préstamos).
        """
        for i in range(self.tabs_depositos.count()):
            tab = self.tabs_depositos.widget(i)
            if isinstance(tab, _TabDeposito):
                tab.recargar()
        if self.tabs_depositos.currentIndex() == self._indice_tab("Resultados"):
            self._buscar()                      # la búsqueda activa también se refresca
        self._actualizar_total()

    def _importar_inventario(self):
        """Abre el asistente de importación desde Excel/CSV (solo admin)."""
        dlg = ImportarDialog(parent=self)
        dlg.exec()
        if dlg.hubo_cambios:
            self._cargar_depositos()

    def _actualizar_total(self):
        tab = self.tabs_depositos.currentWidget()
        if isinstance(tab, _TabDeposito):
            n = tab.tabla.rowCount()
            self.lbl_total.setText(f"{n} ítem(s) en este depósito")
        else:
            self.lbl_total.setText("")

    # ── Búsqueda ───────────────────────────────────────────────────────────────

    def _buscar(self):
        texto = self.input_buscar.text().strip()
        if not texto:
            self._limpiar_busqueda()
            return
        items = self.ctrl_inv.buscar_items(texto)
        idx = self._indice_tab("Resultados")
        if idx >= 0:
            self.tabs_depositos.removeTab(idx)
        tab = _TabResultados(items)
        self.tabs_depositos.addTab(tab, f"🔍  Resultados ({len(items)})")
        self.tabs_depositos.setCurrentWidget(tab)

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

    # ── Acciones de ítems ──────────────────────────────────────────────────────

    def _tab_activa(self):
        tab = self.tabs_depositos.currentWidget()
        return tab if isinstance(tab, _TabDeposito) else None

    def _item_seleccionado(self) -> dict | None:
        tab = self._tab_activa()
        return tab.item_seleccionado() if tab else None

    def _agregar_item(self):
        tab = self._tab_activa()
        if not tab:
            QMessageBox.information(self, "Aviso", "Selecciona un depósito primero.")
            return
        depositos = self.ctrl_dep.obtener_todos()
        dlg = FormularioItem(depositos=depositos, deposito_actual=tab.deposito)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = self.ctrl_inv.agregar_item(dlg.datos())
            if ok:
                tab.recargar()
                self._actualizar_total()
            else:
                QMessageBox.warning(self, "Error", msg)

    def _editar_item(self):
        item = self._item_seleccionado()
        if not item:
            QMessageBox.information(self, "Aviso", "Selecciona un ítem para editar.")
            return
        depositos = self.ctrl_dep.obtener_todos()
        dlg = FormularioItem(depositos=depositos, item_existente=item)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = self.ctrl_inv.editar_item(item["id"], dlg.datos())
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
        historial = self.ctrl_inv.contar_historial(item["id"])
        aviso = (f"\n\nTiene {historial} movimiento(s) en el historial: el historial se conserva "
                 "y el ítem aparecerá marcado como eliminado." if historial else "")
        if QMessageBox.question(
            self, "Confirmar eliminación",
            f"¿Eliminar '{item['nombre']}'?\nEsta acción no se puede deshacer.{aviso}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            ok, msg = self.ctrl_inv.eliminar_item(item["id"])
            if ok:
                tab = self._tab_activa()
                if tab:
                    tab.recargar()
                self._actualizar_total()
            else:
                QMessageBox.warning(self, "No se puede eliminar", msg)

    # ── Estilos ────────────────────────────────────────────────────────────────

    @staticmethod
    def _estilo_tabs():
        return """
            QTabBar::tab {
                background:#DDE2EE; color:#444; padding:8px 18px;
                margin-right:2px; border-top-left-radius:5px; border-top-right-radius:5px;
            }
            QTabBar::tab:selected { background:#4A7ACC; color:white; font-weight:bold; }
            QTabBar::tab:hover:!selected { background:#C5CCE0; }
        """

    @staticmethod
    def _btn_primario():
        return "QPushButton{background:#2E5090;color:white;border-radius:4px;padding:0 14px;font-size:13px;}QPushButton:hover{background:#3A63B0;}"

    @staticmethod
    def _btn_secundario():
        return "QPushButton{background:#EEE;color:#333;border-radius:4px;border:1px solid #CCC;padding:0 14px;font-size:13px;}QPushButton:hover{background:#DDD;}"

    @staticmethod
    def _btn_peligro():
        return "QPushButton{background:#C0392B;color:white;border-radius:4px;padding:0 14px;font-size:13px;}QPushButton:hover{background:#E74C3C;}"

    @staticmethod
    def _btn_admin():
        return "QPushButton{background:#6C3483;color:white;border-radius:4px;padding:0 14px;font-size:13px;}QPushButton:hover{background:#8E44AD;}"


# ─────────────────────────────────────────────────────────────────────────────
#  DIÁLOGO: Gestión de depósitos (solo admin)
# ─────────────────────────────────────────────────────────────────────────────

class GestionDepositos(QDialog):
    """
    Diálogo donde el admin puede crear, editar y eliminar depósitos.
    El nombre es libre: 'Depósito 1', 'Lab Electrónica', 'Salón 201', etc.
    """

    def __init__(self, ctrl: DepositosController, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.setWindowTitle("Gestionar depósitos / espacios")
        self.setMinimumWidth(560)
        self.setMinimumHeight(420)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._construir_ui()
        self._recargar()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        lbl = QLabel("Depósitos / Espacios de almacenamiento")
        lbl.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #2E5090;")
        layout.addWidget(lbl)

        info = QLabel("Puedes llamarlos como quieras: Depósito, Laboratorio, Salón, Vitrina, etc.")
        info.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(info)

        # Tabla de depósitos existentes
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre", "Descripción", "Ítems"])
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setColumnWidth(0, 50)
        self.tabla.setColumnWidth(1, 180)
        self.tabla.setColumnWidth(2, 220)
        self.tabla.setColumnWidth(3, 60)
        self.tabla.setStyleSheet("""
            QTableWidget{background:#FFF;color:#1A1A2E;border:1px solid #DDD;font-size:13px;}
            QTableWidget::item:selected{background:#2E5090;color:white;}
            QHeaderView::section{background:#2E5090;color:white;padding:6px;font-weight:bold;border:none;}
            QTableWidget::item:alternate{background:#F0F4FF;}
        """)
        layout.addWidget(self.tabla)

        # Botones
        btns = QHBoxLayout()
        self.btn_nuevo   = QPushButton("＋  Nuevo depósito")
        self.btn_editar  = QPushButton("✏  Editar")
        self.btn_eliminar = QPushButton("🗑  Eliminar")
        btn_cerrar       = QPushButton("Cerrar")

        self.btn_nuevo.setFixedHeight(36)
        self.btn_editar.setFixedHeight(36)
        self.btn_eliminar.setFixedHeight(36)
        btn_cerrar.setFixedHeight(36)

        self.btn_nuevo.setStyleSheet("QPushButton{background:#2E5090;color:white;border-radius:4px;padding:0 14px;}QPushButton:hover{background:#3A63B0;}")
        self.btn_editar.setStyleSheet("QPushButton{background:#EEE;color:#333;border-radius:4px;border:1px solid #CCC;padding:0 14px;}QPushButton:hover{background:#DDD;}")
        self.btn_eliminar.setStyleSheet("QPushButton{background:#C0392B;color:white;border-radius:4px;padding:0 14px;}QPushButton:hover{background:#E74C3C;}")
        btn_cerrar.setStyleSheet("QPushButton{background:#EEE;color:#333;border-radius:4px;border:1px solid #CCC;padding:0 14px;}QPushButton:hover{background:#DDD;}")

        self.btn_nuevo.clicked.connect(self._nuevo)
        self.btn_editar.clicked.connect(self._editar)
        self.btn_eliminar.clicked.connect(self._eliminar)
        btn_cerrar.clicked.connect(self.accept)

        btns.addWidget(self.btn_nuevo)
        btns.addWidget(self.btn_editar)
        btns.addWidget(self.btn_eliminar)
        btns.addStretch()
        btns.addWidget(btn_cerrar)
        layout.addLayout(btns)

    def _recargar(self):
        depositos = self.ctrl.obtener_todos()
        self.tabla.setRowCount(0)
        for dep in depositos:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)
            for col, valor in enumerate([
                str(dep.get("id", "")),
                dep.get("nombre", ""),
                dep.get("descripcion", "") or "",
                str(dep.get("total_items", 0)),
            ]):
                celda = QTableWidgetItem(valor)
                celda.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.tabla.setItem(fila, col, celda)

    def _seleccionado(self) -> dict | None:
        fila = self.tabla.currentRow()
        if fila < 0:
            return None
        dep_id = int(self.tabla.item(fila, 0).text())
        return self.ctrl.obtener_por_id(dep_id)

    def _nuevo(self):
        dlg = FormularioDeposito()
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = self.ctrl.agregar(dlg.datos())
            if ok:
                self._recargar()
            else:
                QMessageBox.warning(self, "Error", msg)

    def _editar(self):
        dep = self._seleccionado()
        if not dep:
            QMessageBox.information(self, "Aviso", "Selecciona un depósito para editar.")
            return
        dlg = FormularioDeposito(existente=dep)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = self.ctrl.editar(dep["id"], dlg.datos())
            if ok:
                self._recargar()
            else:
                QMessageBox.warning(self, "Error", msg)

    def _eliminar(self):
        dep = self._seleccionado()
        if not dep:
            QMessageBox.information(self, "Aviso", "Selecciona un depósito para eliminar.")
            return
        if QMessageBox.question(
            self, "Confirmar",
            f"¿Eliminar el depósito '{dep['nombre']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            ok, msg = self.ctrl.eliminar(dep["id"])
            if ok:
                self._recargar()
            else:
                QMessageBox.warning(self, "No se puede eliminar", msg)


# ─────────────────────────────────────────────────────────────────────────────
#  FORMULARIO: crear / editar depósito
# ─────────────────────────────────────────────────────────────────────────────

class FormularioDeposito(QDialog):

    def __init__(self, existente: dict = None):
        super().__init__()
        self.setWindowTitle("Editar depósito" if existente else "Nuevo depósito")
        self.setFixedWidth(400)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._construir_ui()
        if existente:
            self.input_nombre.setText(existente.get("nombre", ""))
            self.input_desc.setPlainText(existente.get("descripcion", "") or "")

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.input_nombre = QLineEdit()
        self.input_nombre.setFixedHeight(36)
        self.input_nombre.setPlaceholderText("Ej: Depósito 1, Lab Electrónica, Salón 201...")

        self.input_desc = QTextEdit()
        self.input_desc.setFixedHeight(80)
        self.input_desc.setPlaceholderText("Descripción opcional del espacio...")

        form.addRow("Nombre: *",     self.input_nombre)
        form.addRow("Descripción:",  self.input_desc)
        layout.addLayout(form)

        lbl = QLabel("* El nombre puede ser cualquier identificador del espacio.")
        lbl.setStyleSheet("color:#888; font-size:11px;")
        layout.addWidget(lbl)

        btns = QHBoxLayout()
        btn_c = QPushButton("Cancelar")
        btn_g = QPushButton("Guardar")
        btn_g.setDefault(True)
        btn_c.clicked.connect(self.reject)
        btn_g.clicked.connect(self._ok)
        btn_g.setStyleSheet("QPushButton{background:#2E5090;color:white;border-radius:4px;padding:8px 20px;}QPushButton:hover{background:#3A63B0;}")
        btns.addWidget(btn_c)
        btns.addWidget(btn_g)
        layout.addLayout(btns)

    def _ok(self):
        if not self.input_nombre.text().strip():
            QMessageBox.warning(self, "Campo requerido", "El nombre del depósito es obligatorio.")
            self.input_nombre.setFocus()
            return
        self.accept()

    def datos(self) -> dict:
        return {
            "nombre":      self.input_nombre.text().strip(),
            "descripcion": self.input_desc.toPlainText().strip(),
        }


# ─────────────────────────────────────────────────────────────────────────────
#  PESTAÑA INTERNA: tabla de ítems de un depósito
# ─────────────────────────────────────────────────────────────────────────────

class _TabDeposito(QWidget):

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
        self.tabla.setStyleSheet("""
            QTableWidget{background:#FFF;color:#1A1A2E;border:1px solid #DDD;gridline-color:#EEE;font-size:13px;}
            QTableWidget::item:selected{background:#2E5090;color:white;}
            QHeaderView::section{background:#2E5090;color:white;padding:6px;font-weight:bold;border:none;}
            QTableWidget::item:alternate{background:#F0F4FF;}
            QTableWidget::item{color:#1A1A2E;}
        """)
        for i, w in enumerate([50, 220, 120, 65, 80, 70, 55, 130]):
            self.tabla.setColumnWidth(i, w)

        layout.addWidget(self.tabla)

    def recargar(self):
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
                if col == 4:
                    disp = int(item.get("cantidad_disp", 0))
                    celda.setForeground(QColor("#C0392B") if disp == 0 else
                                        QColor("#E67E22") if disp <= 2 else
                                        QColor("#1A1A2E"))
                self.tabla.setItem(fila, col, celda)

    def item_seleccionado(self) -> dict | None:
        fila = self.tabla.currentRow()
        if fila < 0:
            return None
        return self.controller.obtener_item_por_id(
            int(self.tabla.item(fila, 0).text())
        )


# ─────────────────────────────────────────────────────────────────────────────
#  PESTAÑA TEMPORAL: resultados de búsqueda
# ─────────────────────────────────────────────────────────────────────────────

class _TabResultados(QWidget):

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
        self.tabla.setStyleSheet("""
            QTableWidget{background:#FFF;color:#1A1A2E;border:1px solid #DDD;font-size:13px;}
            QTableWidget::item:selected{background:#2E5090;color:white;}
            QHeaderView::section{background:#2E5090;color:white;padding:6px;font-weight:bold;border:none;}
            QTableWidget::item:alternate{background:#F0F4FF;}
            QTableWidget::item{color:#1A1A2E;}
        """)
        self.tabla.setRowCount(0)
        for item in items:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)
            for col, valor in enumerate([
                str(item.get("id", "")), item.get("deposito", ""),
                item.get("nombre", ""), item.get("referencia", "") or "",
                str(item.get("cantidad_total", 0)), str(item.get("cantidad_disp", 0)),
                str(item.get("cantidad_prest", 0)), item.get("ubicacion", "") or "",
            ]):
                self.tabla.setItem(fila, col, QTableWidgetItem(valor))
        layout.addWidget(self.tabla)


# ─────────────────────────────────────────────────────────────────────────────
#  FORMULARIO: agregar / editar ítem
# ─────────────────────────────────────────────────────────────────────────────

class FormularioItem(QDialog):

    def __init__(self, depositos: list[dict], deposito_actual: dict = None, item_existente: dict = None):
        super().__init__()
        self._depositos       = depositos
        self._deposito_actual = deposito_actual
        self._item            = item_existente
        self._modo_edicion    = item_existente is not None
        self.setWindowTitle("Editar ítem" if self._modo_edicion else "Agregar ítem")
        self.setFixedWidth(420)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._construir_ui()
        if self._modo_edicion:
            self._rellenar(item_existente)

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.combo_deposito = QComboBox()
        self.combo_deposito.setFixedHeight(34)
        for dep in self._depositos:
            self.combo_deposito.addItem(dep["nombre"], userData=dep["id"])
        if self._deposito_actual:
            idx = self.combo_deposito.findText(self._deposito_actual["nombre"])
            if idx >= 0:
                self.combo_deposito.setCurrentIndex(idx)
        if self._modo_edicion:
            self.combo_deposito.setEnabled(False)

        self.input_nombre     = QLineEdit(); self.input_nombre.setFixedHeight(34)
        self.input_referencia = QLineEdit(); self.input_referencia.setFixedHeight(34)
        self.input_ubicacion  = QLineEdit(); self.input_ubicacion.setFixedHeight(34)
        self.spin_cantidad    = QSpinBox();  self.spin_cantidad.setFixedHeight(34)
        self.spin_cantidad.setMinimum(0);    self.spin_cantidad.setMaximum(9999)
        self.txt_obs          = QTextEdit(); self.txt_obs.setFixedHeight(70)

        form.addRow("Depósito: *",    self.combo_deposito)
        form.addRow("Nombre: *",      self.input_nombre)
        form.addRow("Referencia:",    self.input_referencia)
        form.addRow("Cantidad:",      self.spin_cantidad)
        form.addRow("Ubicación:",     self.input_ubicacion)
        form.addRow("Observaciones:", self.txt_obs)
        layout.addLayout(form)

        lbl = QLabel("* Campos obligatorios")
        lbl.setStyleSheet("color:#888; font-size:11px;")
        layout.addWidget(lbl)

        btns = QHBoxLayout()
        btn_c = QPushButton("Cancelar"); btn_c.clicked.connect(self.reject)
        btn_g = QPushButton("Guardar");  btn_g.setDefault(True); btn_g.clicked.connect(self._ok)
        btn_g.setStyleSheet("QPushButton{background:#2E5090;color:white;border-radius:4px;padding:8px 20px;}QPushButton:hover{background:#3A63B0;}")
        btns.addWidget(btn_c); btns.addWidget(btn_g)
        layout.addLayout(btns)

    def _rellenar(self, item: dict):
        self.input_nombre.setText(item.get("nombre", ""))
        self.input_referencia.setText(item.get("referencia", "") or "")
        self.spin_cantidad.setValue(int(item.get("cantidad_total", 0)))
        self.input_ubicacion.setText(item.get("ubicacion", "") or "")
        self.txt_obs.setPlainText(item.get("observaciones", "") or "")

    def _ok(self):
        if not self.input_nombre.text().strip():
            QMessageBox.warning(self, "Campo requerido", "El nombre del ítem es obligatorio.")
            return
        self.accept()

    def datos(self) -> dict:
        return {
            "deposito_id":    self.combo_deposito.currentData(),
            "nombre":         self.input_nombre.text().strip(),
            "referencia":     self.input_referencia.text().strip(),
            "cantidad_total": self.spin_cantidad.value(),
            "ubicacion":      self.input_ubicacion.text().strip(),
            "observaciones":  self.txt_obs.toPlainText().strip(),
        }
