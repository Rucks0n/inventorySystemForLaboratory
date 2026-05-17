"""
app/ui/docentes_view.py
------------------------
Pestaña de gestión de docentes y usuarios (solicitantes).
Dos sub-pestañas: Docentes | Usuarios/Solicitantes.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QMessageBox,
    QDialog, QFormLayout, QAbstractItemView, QComboBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui  import QFont

from app.controllers.docentes_controller import DocentesController, UsuariosController
from app.utils.logger                     import log


class DocentesView(QWidget):

    def __init__(self, usuario: dict):
        super().__init__()
        self.usuario    = usuario
        self.ctrl_doc   = DocentesController()
        self.ctrl_usr   = UsuariosController()
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl = QLabel("Docentes y Usuarios")
        lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #2E5090;")
        layout.addWidget(lbl)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { background:#DDE2EE; color:#444; padding:8px 18px; margin-right:2px;
                border-top-left-radius:5px; border-top-right-radius:5px; }
            QTabBar::tab:selected { background:#4A7ACC; color:white; font-weight:bold; }
            QTabBar::tab:hover:!selected { background:#C5CCE0; }
        """)

        self.tab_docentes = _TabDocentes(self.ctrl_doc)
        self.tab_usuarios = _TabUsuarios(self.ctrl_usr)

        self.tabs.addTab(self.tab_docentes, "🎓  Docentes")
        self.tabs.addTab(self.tab_usuarios, "👤  Solicitantes")
        layout.addWidget(self.tabs)


# ─────────────────────────────────────────────────────────────────────────────
#  SUB-PESTAÑA: Docentes
# ─────────────────────────────────────────────────────────────────────────────

class _TabDocentes(QWidget):

    COLUMNAS = ["ID", "Nombre", "Correo", "Motivo habitual", "Activo"]

    def __init__(self, ctrl: DocentesController):
        super().__init__()
        self.ctrl = ctrl
        self._construir_ui()
        self.recargar()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)

        # Buscador
        barra = QHBoxLayout()
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("🔍  Buscar docente...")
        self.input_buscar.setFixedHeight(34)
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._buscar)
        self.input_buscar.textChanged.connect(lambda: self._timer.start(350))
        barra.addWidget(self.input_buscar)
        layout.addLayout(barra)

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
        self.tabla.setColumnWidth(0, 50)
        self.tabla.setColumnWidth(1, 220)
        self.tabla.setColumnWidth(2, 220)
        self.tabla.setColumnWidth(3, 160)
        layout.addWidget(self.tabla)

        # Acciones
        acciones = QHBoxLayout()
        self.btn_agregar    = QPushButton("＋  Agregar")
        self.btn_editar     = QPushButton("✏  Editar")
        self.btn_desactivar = QPushButton("🚫  Desactivar")
        for btn in [self.btn_agregar, self.btn_editar, self.btn_desactivar]:
            btn.setFixedHeight(36)
        self.btn_agregar.setStyleSheet(self._estilo_primario())
        self.btn_editar.setStyleSheet(self._estilo_secundario())
        self.btn_desactivar.setStyleSheet(self._estilo_peligro())
        self.btn_agregar.clicked.connect(self._agregar)
        self.btn_editar.clicked.connect(self._editar)
        self.btn_desactivar.clicked.connect(self._desactivar)
        acciones.addWidget(self.btn_agregar)
        acciones.addWidget(self.btn_editar)
        acciones.addWidget(self.btn_desactivar)
        acciones.addStretch()
        layout.addLayout(acciones)

    def recargar(self, lista=None):
        datos = lista if lista is not None else self.ctrl.obtener_todos()
        self.tabla.setRowCount(0)
        for d in datos:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)
            for col, valor in enumerate([
                str(d.get("id", "")), d.get("nombre", ""),
                d.get("correo", ""), d.get("motivo", "") or "",
                "Sí" if d.get("activo", 1) else "No"
            ]):
                self.tabla.setItem(fila, col, QTableWidgetItem(valor))

    def _buscar(self):
        texto = self.input_buscar.text().strip()
        if texto:
            self.recargar(self.ctrl.buscar(texto))
        else:
            self.recargar()

    def _seleccionado(self) -> dict | None:
        fila = self.tabla.currentRow()
        if fila < 0:
            return None
        return self.ctrl.obtener_por_id(int(self.tabla.item(fila, 0).text()))

    def _agregar(self):
        dlg = FormularioDocente()
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = self.ctrl.agregar(dlg.datos())
            if ok:
                self.recargar()
            else:
                QMessageBox.warning(self, "Error", msg)

    def _editar(self):
        doc = self._seleccionado()
        if not doc:
            QMessageBox.information(self, "Aviso", "Selecciona un docente.")
            return
        dlg = FormularioDocente(existente=doc)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = self.ctrl.editar(doc["id"], dlg.datos())
            if ok:
                self.recargar()
            else:
                QMessageBox.warning(self, "Error", msg)

    def _desactivar(self):
        doc = self._seleccionado()
        if not doc:
            QMessageBox.information(self, "Aviso", "Selecciona un docente.")
            return
        if QMessageBox.question(self, "Confirmar",
            f"¿Desactivar a '{doc['nombre']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            ok, msg = self.ctrl.desactivar(doc["id"])
            if ok:
                self.recargar()
            else:
                QMessageBox.warning(self, "Error", msg)

    @staticmethod
    def _estilo_tabla():
        return ("QTableWidget{border:1px solid #DDD;gridline-color:#EEE;font-size:13px;}"
                "QTableWidget::item:selected{background:#2E5090;color:white;}"
                "QHeaderView::section{background:#2E5090;color:white;padding:6px;font-weight:bold;border:none;}"
                "QTableWidget::item:alternate{background:#F5F7FC;}")

    @staticmethod
    def _estilo_primario():
        return "QPushButton{background:#2E5090;color:white;border-radius:4px;padding:0 14px;font-size:13px;}QPushButton:hover{background:#3A63B0;}"

    @staticmethod
    def _estilo_secundario():
        return "QPushButton{background:#EEE;color:#333;border-radius:4px;border:1px solid #CCC;padding:0 14px;font-size:13px;}QPushButton:hover{background:#DDD;}"

    @staticmethod
    def _estilo_peligro():
        return "QPushButton{background:#C0392B;color:white;border-radius:4px;padding:0 14px;font-size:13px;}QPushButton:hover{background:#E74C3C;}"


# ─────────────────────────────────────────────────────────────────────────────
#  SUB-PESTAÑA: Usuarios / Solicitantes
# ─────────────────────────────────────────────────────────────────────────────

class _TabUsuarios(QWidget):

    COLUMNAS = ["ID", "Nombre", "Código", "Correo", "Teléfono", "Rol"]

    def __init__(self, ctrl: UsuariosController):
        super().__init__()
        self.ctrl = ctrl
        self._construir_ui()
        self.recargar()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)

        barra = QHBoxLayout()
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("🔍  Buscar por nombre o código...")
        self.input_buscar.setFixedHeight(34)
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._buscar)
        self.input_buscar.textChanged.connect(lambda: self._timer.start(350))
        barra.addWidget(self.input_buscar)
        layout.addLayout(barra)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setStyleSheet(_TabDocentes._estilo_tabla())
        self.tabla.setColumnWidth(0, 50)
        self.tabla.setColumnWidth(1, 200)
        self.tabla.setColumnWidth(2, 120)
        self.tabla.setColumnWidth(3, 200)
        self.tabla.setColumnWidth(4, 120)
        layout.addWidget(self.tabla)

        acciones = QHBoxLayout()
        self.btn_agregar    = QPushButton("＋  Agregar")
        self.btn_editar     = QPushButton("✏  Editar")
        self.btn_desactivar = QPushButton("🚫  Desactivar")
        for btn in [self.btn_agregar, self.btn_editar, self.btn_desactivar]:
            btn.setFixedHeight(36)
        self.btn_agregar.setStyleSheet(_TabDocentes._estilo_primario())
        self.btn_editar.setStyleSheet(_TabDocentes._estilo_secundario())
        self.btn_desactivar.setStyleSheet(_TabDocentes._estilo_peligro())
        self.btn_agregar.clicked.connect(self._agregar)
        self.btn_editar.clicked.connect(self._editar)
        self.btn_desactivar.clicked.connect(self._desactivar)
        acciones.addWidget(self.btn_agregar)
        acciones.addWidget(self.btn_editar)
        acciones.addWidget(self.btn_desactivar)
        acciones.addStretch()
        layout.addLayout(acciones)

    def recargar(self, lista=None):
        datos = lista if lista is not None else self.ctrl.obtener_todos()
        self.tabla.setRowCount(0)
        for u in datos:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)
            for col, valor in enumerate([
                str(u.get("id", "")), u.get("nombre", ""),
                u.get("codigo", ""), u.get("correo", "") or "",
                u.get("telefono", "") or "", u.get("rol", "usuario")
            ]):
                self.tabla.setItem(fila, col, QTableWidgetItem(valor))

    def _buscar(self):
        texto = self.input_buscar.text().strip()
        self.recargar(self.ctrl.buscar(texto) if texto else None)

    def _seleccionado(self) -> dict | None:
        fila = self.tabla.currentRow()
        if fila < 0:
            return None
        return self.ctrl.obtener_por_id(int(self.tabla.item(fila, 0).text()))

    def _agregar(self):
        dlg = FormularioUsuario()
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = self.ctrl.agregar(dlg.datos())
            if ok:
                self.recargar()
            else:
                QMessageBox.warning(self, "Error", msg)

    def _editar(self):
        usr = self._seleccionado()
        if not usr:
            QMessageBox.information(self, "Aviso", "Selecciona un usuario.")
            return
        dlg = FormularioUsuario(existente=usr)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = self.ctrl.editar(usr["id"], dlg.datos())
            if ok:
                self.recargar()
            else:
                QMessageBox.warning(self, "Error", msg)

    def _desactivar(self):
        usr = self._seleccionado()
        if not usr:
            QMessageBox.information(self, "Aviso", "Selecciona un usuario.")
            return
        if QMessageBox.question(self, "Confirmar",
            f"¿Desactivar a '{usr['nombre']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            ok, msg = self.ctrl.desactivar(usr["id"])
            if ok:
                self.recargar()
            else:
                QMessageBox.warning(self, "Error", msg)


# ─────────────────────────────────────────────────────────────────────────────
#  FORMULARIOS
# ─────────────────────────────────────────────────────────────────────────────

class FormularioDocente(QDialog):

    def __init__(self, existente: dict = None):
        super().__init__()
        self._existente = existente
        self.setWindowTitle("Editar docente" if existente else "Agregar docente")
        self.setFixedWidth(400)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._construir_ui()
        if existente:
            self.input_nombre.setText(existente.get("nombre", ""))
            self.input_correo.setText(existente.get("correo", ""))
            self.input_motivo.setText(existente.get("motivo", "") or "")

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        form = QFormLayout()
        form.setSpacing(10)
        self.input_nombre = QLineEdit(); self.input_nombre.setFixedHeight(34)
        self.input_correo = QLineEdit(); self.input_correo.setFixedHeight(34)
        self.input_motivo = QLineEdit(); self.input_motivo.setFixedHeight(34)
        self.input_motivo.setPlaceholderText("Ej: Clases, Tutorías, Investigación...")
        form.addRow("Nombre: *",  self.input_nombre)
        form.addRow("Correo: *",  self.input_correo)
        form.addRow("Motivo:",    self.input_motivo)
        layout.addLayout(form)
        btns = QHBoxLayout()
        btn_c = QPushButton("Cancelar"); btn_c.clicked.connect(self.reject)
        btn_g = QPushButton("Guardar");  btn_g.setDefault(True); btn_g.clicked.connect(self._ok)
        btn_g.setStyleSheet("QPushButton{background:#2E5090;color:white;border-radius:4px;padding:8px 16px;}QPushButton:hover{background:#3A63B0;}")
        btns.addWidget(btn_c); btns.addWidget(btn_g)
        layout.addLayout(btns)

    def _ok(self):
        if not self.input_nombre.text().strip() or not self.input_correo.text().strip():
            QMessageBox.warning(self, "Requerido", "Nombre y correo son obligatorios.")
            return
        self.accept()

    def datos(self) -> dict:
        return {"nombre": self.input_nombre.text().strip(),
                "correo": self.input_correo.text().strip(),
                "motivo": self.input_motivo.text().strip()}


class FormularioUsuario(QDialog):

    def __init__(self, existente: dict = None):
        super().__init__()
        self._existente = existente
        self.setWindowTitle("Editar usuario" if existente else "Agregar usuario")
        self.setFixedWidth(400)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._construir_ui()
        if existente:
            self.input_nombre.setText(existente.get("nombre", ""))
            self.input_codigo.setText(existente.get("codigo", ""))
            self.input_correo.setText(existente.get("correo", "") or "")
            self.input_tel.setText(existente.get("telefono", "") or "")

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        form = QFormLayout(); form.setSpacing(10)
        self.input_nombre = QLineEdit(); self.input_nombre.setFixedHeight(34)
        self.input_codigo = QLineEdit(); self.input_codigo.setFixedHeight(34)
        self.input_correo = QLineEdit(); self.input_correo.setFixedHeight(34)
        self.input_tel    = QLineEdit(); self.input_tel.setFixedHeight(34)
        if self._existente:
            self.input_codigo.setEnabled(False)
        form.addRow("Nombre: *", self.input_nombre)
        form.addRow("Código: *", self.input_codigo)
        form.addRow("Correo:",   self.input_correo)
        form.addRow("Teléfono:", self.input_tel)
        layout.addLayout(form)
        btns = QHBoxLayout()
        btn_c = QPushButton("Cancelar"); btn_c.clicked.connect(self.reject)
        btn_g = QPushButton("Guardar");  btn_g.setDefault(True); btn_g.clicked.connect(self._ok)
        btn_g.setStyleSheet("QPushButton{background:#2E5090;color:white;border-radius:4px;padding:8px 16px;}QPushButton:hover{background:#3A63B0;}")
        btns.addWidget(btn_c); btns.addWidget(btn_g)
        layout.addLayout(btns)

    def _ok(self):
        if not self.input_nombre.text().strip() or not self.input_codigo.text().strip():
            QMessageBox.warning(self, "Requerido", "Nombre y código son obligatorios.")
            return
        self.accept()

    def datos(self) -> dict:
        return {"nombre":   self.input_nombre.text().strip(),
                "codigo":   self.input_codigo.text().strip(),
                "correo":   self.input_correo.text().strip(),
                "telefono": self.input_tel.text().strip()}
