"""
app/ui/importar/paso_destino.py
-------------------------------
Paso 3: en qué depósito va cada ítem, qué tipo tienen por defecto y qué hacer
con los que ya existen.

Tres formas de repartir en depósitos (según cómo venga el Excel):
    hojas    cada hoja del archivo es un depósito (la hoja se llama como el depósito)
    columna  una columna del archivo dice el depósito de cada fila
    unico    todo el archivo va a un solo depósito
"""

from PyQt6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel,
    QRadioButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from app.controllers.tipos_controller import TiposController
from app.services.importador.catalogo import cargar_catalogo
from app.services.importador.texto import clave
from app.ui.importar.base import Paso
from config.constants import (
    COMP_PRESTA, IMP_DEPOSITO_POR_COLUMNA, IMP_DEPOSITO_POR_HOJA, IMP_DEPOSITO_UNICO,
    IMP_DUP_ACTUALIZAR, IMP_DUP_OMITIR,
)


class PasoDestino(Paso):
    titulo = "Depósitos y opciones"
    ayuda = "Dile al programa en qué depósito va cada ítem y qué hacer con los que ya existen."

    def __init__(self, estado):
        super().__init__(estado)
        self._llave = None
        self._catalogo = None

        # ── ¿En qué depósito va cada ítem? ──
        caja = QGroupBox("¿En qué depósito va cada ítem?")
        capa = QVBoxLayout(caja)
        self.rb_hojas = QRadioButton("Cada hoja del archivo es un depósito (la hoja se llama "
                                     "igual que el depósito)")
        self.rb_columna = QRadioButton("Una columna del archivo dice el depósito de cada fila")
        self.rb_unico = QRadioButton("Todo el archivo va al mismo depósito:")
        self.grupo_modo = QButtonGroup(self)
        for rb in (self.rb_hojas, self.rb_columna, self.rb_unico):
            self.grupo_modo.addButton(rb)
            rb.toggled.connect(self._refrescar)

        self.combo_unico = QComboBox()
        self.combo_unico.setEditable(True)
        self.combo_unico.setMinimumWidth(260)
        self.combo_unico.setToolTip("Elige uno de la lista o escribe el nombre de uno nuevo.")
        self.combo_unico.editTextChanged.connect(self._refrescar)
        fila_unico = QHBoxLayout()
        fila_unico.addWidget(self.rb_unico)
        fila_unico.addWidget(self.combo_unico)
        fila_unico.addStretch()

        self.tabla_hojas = QTableWidget(0, 2)
        self.tabla_hojas.setHorizontalHeaderLabels(["Hoja del archivo", "Depósito"])
        self.tabla_hojas.horizontalHeader().setStretchLastSection(True)
        self.tabla_hojas.setColumnWidth(0, 240)
        self.tabla_hojas.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_hojas.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tabla_hojas.setMaximumHeight(130)
        self.lbl_columna = QLabel("")
        self.lbl_columna.setWordWrap(True)
        self.lbl_columna.setStyleSheet("color:#777;")

        capa.addWidget(self.rb_hojas)
        capa.addWidget(self.tabla_hojas)
        capa.addWidget(self.rb_columna)
        capa.addWidget(self.lbl_columna)
        capa.addLayout(fila_unico)
        self.chk_crear = QCheckBox("Crear los depósitos que no existan todavía")
        self.chk_crear.toggled.connect(self._refrescar)
        capa.addWidget(self.chk_crear)
        self.cuerpo.addWidget(caja)

        # ── Tipo por defecto ──
        caja_tipo = QGroupBox("Tipo de ítem")
        fila_tipo = QHBoxLayout(caja_tipo)
        fila_tipo.addWidget(QLabel("Si una fila no dice su tipo, se guarda como:"))
        self.combo_tipo = QComboBox()
        self.combo_tipo.setMinimumWidth(320)
        fila_tipo.addWidget(self.combo_tipo)
        fila_tipo.addStretch()
        self.cuerpo.addWidget(caja_tipo)

        # ── Ítems que ya existen ──
        caja_dup = QGroupBox("Si el ítem ya existe en el inventario")
        capa_dup = QVBoxLayout(caja_dup)
        self.rb_omitir = QRadioButton("Dejarlo como está (recomendado: así puedes subir el mismo "
                                      "archivo otra vez sin duplicar nada)")
        self.rb_actualizar = QRadioButton("Actualizar su cantidad y sus datos con lo que dice el archivo")
        self.rb_omitir.setChecked(True)
        capa_dup.addWidget(self.rb_omitir)
        capa_dup.addWidget(self.rb_actualizar)
        self.cuerpo.addWidget(caja_dup)
        self.cuerpo.addStretch()

    # ── Entrar al paso ─────────────────────────────────────────────────────────

    def al_entrar(self):
        self._catalogo = cargar_catalogo()
        tiene_columna = "deposito" in self.estado.mapeo
        self.rb_columna.setEnabled(tiene_columna)
        self.rb_columna.setText(
            "Una columna del archivo dice el depósito de cada fila" if tiene_columna else
            "Una columna del archivo dice el depósito (no hay: asígnala en el paso «Columnas»)")

        llave = (self.estado.ruta, tuple(self.estado.hojas_elegidas), tiene_columna)
        if llave != self._llave:
            self._llave = llave
            self._valores_iniciales(tiene_columna)
        self._refrescar()

    def _valores_iniciales(self, tiene_columna: bool):
        """Propone lo más probable según el archivo; el usuario puede cambiarlo."""
        depositos = [nombre for _, nombre in self._catalogo.depositos.values()]
        self.combo_unico.clear()
        self.combo_unico.addItems(depositos)
        if not depositos:
            self.combo_unico.setEditText("")

        coinciden = all(clave(h) in self._catalogo.depositos for h in self.estado.hojas_elegidas)
        if tiene_columna:
            self.rb_columna.setChecked(True)
        elif coinciden or len(self.estado.hojas_elegidas) > 1 or not depositos:
            self.rb_hojas.setChecked(True)
        else:
            self.rb_unico.setChecked(True)
        self.chk_crear.setChecked(not depositos)         # primera importación: no hay depósitos

        self.combo_tipo.clear()
        for tipo in self._catalogo.tipos_por_id.values():
            accion = "se presta" if tipo.comportamiento == COMP_PRESTA else "se consume"
            self.combo_tipo.addItem(f"{tipo.nombre}  ({accion})", tipo.id)
        por_defecto = TiposController().tipo_por_defecto()
        if por_defecto:
            self.combo_tipo.setCurrentIndex(max(self.combo_tipo.findData(por_defecto["id"]), 0))

    # ── Lo que se ve según la opción elegida ───────────────────────────────────

    def _modo(self) -> str:
        if self.rb_columna.isChecked():
            return IMP_DEPOSITO_POR_COLUMNA
        return IMP_DEPOSITO_UNICO if self.rb_unico.isChecked() else IMP_DEPOSITO_POR_HOJA

    def _refrescar(self, *_):
        if self._catalogo is None:
            return
        modo = self._modo()
        self.combo_unico.setEnabled(modo == IMP_DEPOSITO_UNICO)
        self.tabla_hojas.setVisible(modo == IMP_DEPOSITO_POR_HOJA)

        encabezado = self.estado.mapeo.get("deposito")
        self.lbl_columna.setVisible(modo == IMP_DEPOSITO_POR_COLUMNA)
        self.lbl_columna.setText(
            f"Se usará la columna «{encabezado}». Si una celda está vacía (por ejemplo, celdas "
            "combinadas en Excel), se usa el depósito de la fila de arriba."
            if encabezado else "")

        hojas = self.estado.hojas_elegidas
        self.tabla_hojas.setRowCount(len(hojas))
        for fila, hoja in enumerate(hojas):
            existente = self._catalogo.depositos.get(clave(hoja))
            if existente:
                estado = f"✔ {existente[1]}"
            elif self.chk_crear.isChecked():
                estado = "＋ se creará uno nuevo"
            else:
                estado = "✘ no existe (esta hoja no se importará)"
            self.tabla_hojas.setItem(fila, 0, QTableWidgetItem(hoja))
            self.tabla_hojas.setItem(fila, 1, QTableWidgetItem(estado))

    # ── Salir del paso ─────────────────────────────────────────────────────────

    def validar(self) -> bool:
        modo = self._modo()
        deposito = " ".join(self.combo_unico.currentText().split())
        if modo == IMP_DEPOSITO_UNICO:
            if not deposito:
                return self.avisar("Elige o escribe el depósito donde se guardarán los ítems.")
            if clave(deposito) not in self._catalogo.depositos and not self.chk_crear.isChecked():
                return self.avisar(f"El depósito «{deposito}» no existe. Elige uno de la lista o "
                                   "marca «Crear los depósitos que no existan todavía».")

        self.estado.modo_deposito = modo
        self.estado.deposito_unico = deposito if modo == IMP_DEPOSITO_UNICO else None
        self.estado.crear_depositos = self.chk_crear.isChecked()
        self.estado.tipo_defecto_id = self.combo_tipo.currentData()
        self.estado.politica = IMP_DUP_ACTUALIZAR if self.rb_actualizar.isChecked() else IMP_DUP_OMITIR
        return True
