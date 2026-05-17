"""
app/ui/prestamos_view.py
-------------------------
Pestaña de gestión de préstamos y devoluciones.
Dos sub-pestañas: Activos | Historial de movimientos.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QLineEdit, QLabel, QMessageBox,
    QDialog, QFormLayout, QSpinBox, QTextEdit,
    QComboBox, QAbstractItemView, QDateEdit
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui  import QFont, QColor

from app.controllers.prestamos_controller   import PrestamosController
from app.controllers.inventario_controller  import InventarioController
from app.controllers.docentes_controller    import DocentesController, UsuariosController
from app.utils.logger                        import log


class PrestamosView(QWidget):
    """Vista principal de préstamos."""

    def __init__(self, usuario: dict):
        super().__init__()
        self.usuario      = usuario
        self.ctrl_prest   = PrestamosController()
        self.ctrl_inv     = InventarioController()
        self.ctrl_doc     = DocentesController()
        self.ctrl_usr     = UsuariosController()
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Título
        lbl = QLabel("Préstamos y Devoluciones")
        lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #2E5090;")
        layout.addWidget(lbl)

        # Sub-pestañas
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(self._estilo_tabs())

        self.tab_activos   = _TabActivos(self.ctrl_prest, self.ctrl_inv,
                                         self.ctrl_doc, self.ctrl_usr, self.usuario)
        self.tab_historial = _TabHistorial(self.ctrl_prest)

        self.tabs.addTab(self.tab_activos,   "📋  Préstamos activos")
        self.tabs.addTab(self.tab_historial, "📜  Historial de movimientos")

        # Recargar historial al cambiar de pestaña
        self.tabs.currentChanged.connect(self._al_cambiar_tab)
        layout.addWidget(self.tabs)

    def _al_cambiar_tab(self, idx: int):
        if idx == 1:
            self.tab_historial.recargar()

    @staticmethod
    def _estilo_tabs():
        return """
            QTabBar::tab {
                background: #DDE2EE; color: #444;
                padding: 8px 18px; margin-right: 2px;
                border-top-left-radius: 5px; border-top-right-radius: 5px;
            }
            QTabBar::tab:selected { background: #4A7ACC; color: white; font-weight: bold; }
            QTabBar::tab:hover:!selected { background: #C5CCE0; }
        """


# ─────────────────────────────────────────────────────────────────────────────
#  SUB-PESTAÑA: Activos
# ─────────────────────────────────────────────────────────────────────────────

class _TabActivos(QWidget):

    COLUMNAS = ["ID", "Ítem", "Ref.", "Cant.", "Usuario", "Código",
                "Teléfono", "Docente", "Motivo", "Fecha", "Límite"]

    def __init__(self, ctrl_prest, ctrl_inv, ctrl_doc, ctrl_usr, usuario):
        super().__init__()
        self.ctrl_prest = ctrl_prest
        self.ctrl_inv   = ctrl_inv
        self.ctrl_doc   = ctrl_doc
        self.ctrl_usr   = ctrl_usr
        self.usuario    = usuario
        self._construir_ui()
        self.recargar()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)

        # Tabla
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

        anchos = [50, 200, 100, 55, 160, 100, 100, 140, 120, 140, 100]
        for i, w in enumerate(anchos):
            self.tabla.setColumnWidth(i, w)

        layout.addWidget(self.tabla)

        # Acciones
        acciones = QHBoxLayout()
        self.btn_nuevo     = QPushButton("＋  Nuevo préstamo")
        self.btn_devolver  = QPushButton("✔  Registrar devolución")
        self.btn_recargar  = QPushButton("↺  Actualizar")
        self.lbl_total     = QLabel("")

        self.btn_nuevo.setFixedHeight(36)
        self.btn_devolver.setFixedHeight(36)
        self.btn_recargar.setFixedHeight(36)

        self.btn_nuevo.setStyleSheet(self._estilo_btn_primario())
        self.btn_devolver.setStyleSheet(self._estilo_btn_verde())
        self.btn_recargar.setStyleSheet(self._estilo_btn_secundario())
        self.lbl_total.setStyleSheet("color: #666; font-size: 12px;")

        self.btn_nuevo.clicked.connect(self._nuevo_prestamo)
        self.btn_devolver.clicked.connect(self._registrar_devolucion)
        self.btn_recargar.clicked.connect(self.recargar)

        acciones.addWidget(self.btn_nuevo)
        acciones.addWidget(self.btn_devolver)
        acciones.addWidget(self.btn_recargar)
        acciones.addStretch()
        acciones.addWidget(self.lbl_total)
        layout.addLayout(acciones)

    def recargar(self):
        prestamos = self.ctrl_prest.obtener_activos()
        self.tabla.setRowCount(0)
        for p in prestamos:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)
            valores = [
                str(p.get("id", "")),
                p.get("item_nombre", ""),
                p.get("item_ref", "") or "",
                str(p.get("cantidad", 0)),
                p.get("usuario_nombre", ""),
                p.get("usuario_codigo", "") or "",
                p.get("usuario_telefono", "") or "",
                p.get("docente_nombre", "") or "",
                p.get("motivo", "") or "",
                str(p.get("fecha_prestamo", ""))[:16],
                str(p.get("fecha_limite", "") or ""),
            ]
            for col, valor in enumerate(valores):
                celda = QTableWidgetItem(valor)
                celda.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.tabla.setItem(fila, col, celda)

        self.lbl_total.setText(f"{len(prestamos)} préstamo(s) activo(s)")

    def _prestamo_seleccionado(self) -> dict | None:
        fila = self.tabla.currentRow()
        if fila < 0:
            return None
        pid = int(self.tabla.item(fila, 0).text())
        return self.ctrl_prest.obtener_por_id(pid)

    def _nuevo_prestamo(self):
        items     = self.ctrl_inv.obtener_todos_los_items()
        docentes  = self.ctrl_doc.obtener_todos()
        dlg = FormularioPrestamo(items=items, docentes=docentes, ctrl_usr=self.ctrl_usr)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            datos = dlg.datos()
            datos["usuario_id"] = self._asegurar_usuario(dlg)
            if not datos["usuario_id"]:
                return
            ok, msg = self.ctrl_prest.registrar_prestamo(datos)
            if ok:
                self.recargar()
                QMessageBox.information(self, "Éxito", "Préstamo registrado correctamente.")
            else:
                QMessageBox.warning(self, "Error", msg)

    def _asegurar_usuario(self, dlg: "FormularioPrestamo") -> int | None:
        """Busca o crea el usuario solicitante por código."""
        codigo = dlg.input_codigo.text().strip()
        nombre = dlg.input_nombre_usr.text().strip()
        if not codigo:
            QMessageBox.warning(self, "Error", "El código del solicitante es obligatorio.")
            return None
        usr = self.ctrl_usr.buscar_por_codigo(codigo)
        if usr:
            return usr["id"]
        # Crear automáticamente si no existe
        ok, msg = self.ctrl_usr.agregar({"nombre": nombre or codigo, "codigo": codigo,
                                          "telefono": dlg.input_tel.text().strip()})
        if ok:
            return self.ctrl_usr.buscar_por_codigo(codigo)["id"]
        QMessageBox.warning(self, "Error creando usuario", msg)
        return None

    def _registrar_devolucion(self):
        prestamo = self._prestamo_seleccionado()
        if not prestamo:
            QMessageBox.information(self, "Aviso", "Selecciona un préstamo activo.")
            return
        confirm = QMessageBox.question(
            self, "Confirmar devolución",
            f"¿Registrar devolución del ítem '{prestamo.get('item_nombre', '')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            ok, msg = self.ctrl_prest.registrar_devolucion(prestamo["id"])
            if ok:
                self.recargar()
                QMessageBox.information(self, "Éxito", "Devolución registrada correctamente.")
            else:
                QMessageBox.warning(self, "Error", msg)

    @staticmethod
    def _estilo_tabla():
        return """
            QTableWidget { border: 1px solid #DDD; gridline-color: #EEE; font-size: 13px; }
            QTableWidget::item:selected { background: #2E5090; color: white; }
            QHeaderView::section { background: #2E5090; color: white; padding: 6px; font-weight: bold; border: none; }
            QTableWidget::item:alternate { background: #F5F7FC; }
        """

    @staticmethod
    def _estilo_btn_primario():
        return "QPushButton { background:#2E5090; color:white; border-radius:4px; padding:0 14px; font-size:13px; } QPushButton:hover{background:#3A63B0;}"

    @staticmethod
    def _estilo_btn_verde():
        return "QPushButton { background:#27AE60; color:white; border-radius:4px; padding:0 14px; font-size:13px; } QPushButton:hover{background:#2ECC71;}"

    @staticmethod
    def _estilo_btn_secundario():
        return "QPushButton { background:#EEE; color:#555; border-radius:4px; border:1px solid #CCC; padding:0 14px; font-size:13px; } QPushButton:hover{background:#DDD;}"


# ─────────────────────────────────────────────────────────────────────────────
#  SUB-PESTAÑA: Historial
# ─────────────────────────────────────────────────────────────────────────────

class _TabHistorial(QWidget):

    COLUMNAS = ["ID", "Fecha", "Tipo", "Ítem", "Ref.", "Cant.", "Usuario", "Código", "Docente", "Motivo"]

    def __init__(self, ctrl_prest: PrestamosController):
        super().__init__()
        self.ctrl = ctrl_prest
        self._construir_ui()
        self.recargar()

    def _construir_ui(self):
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
        self.tabla.setStyleSheet(_TabActivos._estilo_tabla())

        anchos = [50, 140, 90, 180, 100, 55, 150, 100, 140, 140]
        for i, w in enumerate(anchos):
            self.tabla.setColumnWidth(i, w)

        btn_recargar = QPushButton("↺  Actualizar historial")
        btn_recargar.setFixedHeight(34)
        btn_recargar.setStyleSheet(_TabActivos._estilo_btn_secundario())
        btn_recargar.clicked.connect(self.recargar)

        layout.addWidget(self.tabla)
        layout.addWidget(btn_recargar, alignment=Qt.AlignmentFlag.AlignRight)

    def recargar(self):
        movimientos = self.ctrl.obtener_historial(limite=300)
        self.tabla.setRowCount(0)
        colores_tipo = {"Salida": "#C0392B", "Devolución": "#27AE60", "Entrada": "#2980B9"}
        for m in movimientos:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)
            valores = [
                str(m.get("id", "")),
                str(m.get("fecha", ""))[:16],
                m.get("tipo", ""),
                m.get("item_nombre", "") or "",
                m.get("item_ref", "") or "",
                str(m.get("cantidad", 0)),
                m.get("usuario_nombre", "") or "",
                m.get("usuario_codigo", "") or "",
                m.get("docente_nombre", "") or "",
                m.get("motivo", "") or "",
            ]
            for col, valor in enumerate(valores):
                celda = QTableWidgetItem(valor)
                if col == 2:
                    color = colores_tipo.get(valor, "#333")
                    celda.setForeground(QColor(color))
                self.tabla.setItem(fila, col, celda)


# ─────────────────────────────────────────────────────────────────────────────
#  FORMULARIO: nuevo préstamo
# ─────────────────────────────────────────────────────────────────────────────

class FormularioPrestamo(QDialog):

    def __init__(self, items: list[dict], docentes: list[dict], ctrl_usr: UsuariosController):
        super().__init__()
        self._items   = items
        self._docentes = docentes
        self._ctrl_usr = ctrl_usr
        self.setWindowTitle("Nuevo préstamo")
        self.setFixedWidth(460)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        # Ítem
        self.combo_item = QComboBox()
        self.combo_item.setFixedHeight(34)
        for item in self._items:
            disp = item.get("cantidad_disp", 0)
            label = f"{item['nombre']}  [{item.get('deposito','')}]  — Disp: {disp}"
            self.combo_item.addItem(label, userData=item["id"])

        # Cantidad
        self.spin_cantidad = QSpinBox()
        self.spin_cantidad.setMinimum(1)
        self.spin_cantidad.setMaximum(999)
        self.spin_cantidad.setFixedHeight(34)

        # Solicitante
        self.input_codigo    = QLineEdit()
        self.input_codigo.setPlaceholderText("Código estudiantil")
        self.input_codigo.setFixedHeight(34)
        self.input_codigo.editingFinished.connect(self._buscar_usuario)

        self.input_nombre_usr = QLineEdit()
        self.input_nombre_usr.setPlaceholderText("Nombre completo")
        self.input_nombre_usr.setFixedHeight(34)

        self.input_tel = QLineEdit()
        self.input_tel.setPlaceholderText("Teléfono (opcional)")
        self.input_tel.setFixedHeight(34)

        # Docente
        self.combo_docente = QComboBox()
        self.combo_docente.setFixedHeight(34)
        self.combo_docente.addItem("— Sin docente —", userData=None)
        for d in self._docentes:
            self.combo_docente.addItem(d["nombre"], userData=d["id"])

        # Motivo
        self.input_motivo = QLineEdit()
        self.input_motivo.setPlaceholderText("Ej: Clases, Proyecto, Investigación...")
        self.input_motivo.setFixedHeight(34)

        # Fecha límite
        self.fecha_limite = QDateEdit(QDate.currentDate().addDays(7))
        self.fecha_limite.setCalendarPopup(True)
        self.fecha_limite.setDisplayFormat("dd/MM/yyyy")
        self.fecha_limite.setFixedHeight(34)

        form.addRow("Ítem: *",           self.combo_item)
        form.addRow("Cantidad: *",       self.spin_cantidad)
        form.addRow("Código solicitante:*", self.input_codigo)
        form.addRow("Nombre solicitante:", self.input_nombre_usr)
        form.addRow("Teléfono:",         self.input_tel)
        form.addRow("Docente responsable:", self.combo_docente)
        form.addRow("Motivo:",           self.input_motivo)
        form.addRow("Fecha límite:",     self.fecha_limite)

        layout.addLayout(form)

        lbl = QLabel("* Campos obligatorios")
        lbl.setStyleSheet("color:#999; font-size:11px;")
        layout.addWidget(lbl)

        btns = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_guardar = QPushButton("Registrar préstamo")
        btn_guardar.setDefault(True)
        btn_guardar.clicked.connect(self._validar_y_aceptar)
        btn_guardar.setStyleSheet(
            "QPushButton{background:#2E5090;color:white;border-radius:4px;padding:8px 16px;}"
            "QPushButton:hover{background:#3A63B0;}"
        )
        btns.addWidget(btn_cancelar)
        btns.addWidget(btn_guardar)
        layout.addLayout(btns)

    def _buscar_usuario(self):
        """Auto-rellena nombre y teléfono si el código ya existe en la BD."""
        codigo = self.input_codigo.text().strip()
        if not codigo:
            return
        usr = self._ctrl_usr.buscar_por_codigo(codigo)
        if usr:
            self.input_nombre_usr.setText(usr.get("nombre", ""))
            self.input_tel.setText(usr.get("telefono", "") or "")

    def _validar_y_aceptar(self):
        if not self.input_codigo.text().strip():
            QMessageBox.warning(self, "Campo requerido", "El código del solicitante es obligatorio.")
            return
        self.accept()

    def datos(self) -> dict:
        return {
            "item_id":     self.combo_item.currentData(),
            "cantidad":    self.spin_cantidad.value(),
            "docente_id":  self.combo_docente.currentData(),
            "motivo":      self.input_motivo.text().strip(),
            "fecha_limite": self.fecha_limite.date().toString("yyyy-MM-dd"),
        }
