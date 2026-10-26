"""
app/ui/importar/paso_columnas.py
--------------------------------
Paso 2: decir qué columna del archivo es cada dato (nombre, cantidad, código…).

El programa propone el mapeo mirando los encabezados (ver services/importador/mapeo.py)
o aplicando un formato que el usuario guardó antes. Aquí el usuario lo corrige.
El mapeo se guarda por el TEXTO del encabezado, no por la posición de la columna, así
que sirve igual para todas las hojas aunque tengan las columnas en otro orden.
"""

from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QMessageBox,
    QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
)

from app.services.importador import mapeo as mapeo_mod
from app.services.importador import perfiles
from app.services.importador.campos import CAMPOS
from app.services.importador.lector import fila_vacia
from app.services.importador.texto import limpiar, normalizar
from app.ui.importar.base import ESTILO_SECUNDARIO, Paso

FILAS_DE_EJEMPLO = 8
MAX_FILA_ENCABEZADO = 50


class PasoColumnas(Paso):
    titulo = "Columnas"
    ayuda = ("Indica qué columna del archivo es cada dato. El programa ya propuso una según el "
             "nombre de las columnas; corrige lo que no esté bien. Solo el nombre y la cantidad "
             "son obligatorios.")

    def __init__(self, estado):
        super().__init__(estado)
        self._llave = None            # (archivo, hojas): cuándo hay que volver a proponer
        self._encabezados: list = []
        self._filas_datos: list[list] = []
        self._posiciones: dict[str, int] = {}     # encabezado normalizado → posición
        self._textos: dict[str, str] = {}         # encabezado normalizado → texto original
        self._combos: dict[str, QComboBox] = {}
        self._ejemplos: dict[str, QLabel] = {}

        # Controles de arriba: hoja de referencia y fila de encabezados
        arriba = QHBoxLayout()
        self.lbl_hoja = QLabel("Hoja de ejemplo:")
        self.combo_hoja = QComboBox()
        self.combo_hoja.currentIndexChanged.connect(lambda _: self._leer_hoja(proponer=True))
        arriba.addWidget(self.lbl_hoja)
        arriba.addWidget(self.combo_hoja)
        arriba.addSpacing(16)
        arriba.addWidget(QLabel("Fila de encabezados:"))
        self.spin_fila = QSpinBox()
        self.spin_fila.setRange(0, MAX_FILA_ENCABEZADO)
        self.spin_fila.setSpecialValueText("Automática")
        self.spin_fila.setToolTip("Automática: el programa busca la fila con los nombres de las columnas.\n"
                                  "Si tu archivo tiene títulos arriba y no la encuentra, escribe su número.")
        self.spin_fila.valueChanged.connect(lambda _: self._leer_hoja(proponer=True))
        arriba.addWidget(self.spin_fila)
        arriba.addStretch()
        self.cuerpo.addLayout(arriba)

        self.lbl_perfil = QLabel("")
        self.lbl_perfil.setStyleSheet("color:#2E5090;")
        self.cuerpo.addWidget(self.lbl_perfil)

        # Un renglón por dato: nombre, lista de columnas, ejemplos
        grilla = QGridLayout()
        grilla.setColumnStretch(2, 1)
        grilla.setHorizontalSpacing(12)
        for fila, campo in enumerate(CAMPOS):
            etiqueta = QLabel(campo.etiqueta + (" *" if campo.obligatorio else ""))
            if campo.obligatorio:
                etiqueta.setStyleSheet("font-weight:bold;")
            combo = QComboBox()
            combo.setMinimumWidth(240)
            combo.setMaximumHeight(32)
            combo.currentIndexChanged.connect(lambda _: self._cambio_de_columna())
            ejemplo = QLabel("")
            ejemplo.setStyleSheet("color:#777;")
            self._combos[campo.clave], self._ejemplos[campo.clave] = combo, ejemplo
            grilla.addWidget(etiqueta, fila, 0)
            grilla.addWidget(combo, fila, 1)
            grilla.addWidget(ejemplo, fila, 2)
        self.cuerpo.addLayout(grilla)

        self.lbl_sin_usar = QLabel("")
        self.lbl_sin_usar.setWordWrap(True)
        self.lbl_sin_usar.setStyleSheet("color:#777;")
        self.cuerpo.addWidget(self.lbl_sin_usar)

        # Vista previa de los datos para que el usuario confirme que eligió bien
        self.tabla = QTableWidget()
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tabla.setMinimumHeight(150)
        self.tabla.setMaximumHeight(220)
        self.cuerpo.addWidget(self.tabla)

        abajo = QHBoxLayout()
        self.btn_guardar = QPushButton("💾  Guardar este formato…")
        self.btn_guardar.setFixedHeight(32)
        self.btn_guardar.setStyleSheet(ESTILO_SECUNDARIO)
        self.btn_guardar.setToolTip("Si todos los archivos de un laboratorio tienen estas columnas, "
                                    "guárdalas con un nombre y la próxima vez se aplicarán solas.")
        self.btn_guardar.clicked.connect(self._guardar_formato)
        abajo.addWidget(self.btn_guardar)
        abajo.addStretch()
        self.cuerpo.addLayout(abajo)

    # ── Entrar al paso ─────────────────────────────────────────────────────────

    def al_entrar(self):
        llave = (self.estado.ruta, tuple(self.estado.hojas_elegidas))
        nuevo = llave != self._llave
        if nuevo:
            self._llave = llave
            self.combo_hoja.blockSignals(True)
            self.combo_hoja.clear()
            self.combo_hoja.addItems(self.estado.hojas_elegidas)
            self.combo_hoja.blockSignals(False)
            hay_varias = len(self.estado.hojas_elegidas) > 1
            self.lbl_hoja.setVisible(hay_varias)
            self.combo_hoja.setVisible(hay_varias)
            self.spin_fila.blockSignals(True)
            self.spin_fila.setValue(0)
            self.spin_fila.blockSignals(False)
        self._leer_hoja(proponer=nuevo)

    def _leer_hoja(self, proponer: bool):
        """Lee los encabezados de la hoja de ejemplo y (si hace falta) propone el mapeo."""
        previa = self.estado.previas.get(self.combo_hoja.currentText(), [])
        fila = mapeo_mod.elegir_fila_encabezado(previa, self.spin_fila.value() or None)
        self._encabezados = previa[fila - 1] if fila and fila <= len(previa) else []
        self._filas_datos = [f for f in previa[fila:] if not fila_vacia(f)] if fila else []

        self._posiciones, self._textos = {}, {}
        for posicion, encabezado in enumerate(self._encabezados):
            normal = normalizar(encabezado)
            if normal and normal not in self._posiciones:
                self._posiciones[normal] = posicion
                self._textos[normal] = str(encabezado).strip()

        if proponer:
            nombre_perfil, propuesta = mapeo_mod.proponer_mapeo(self._encabezados, perfiles.listar())
            self.estado.mapeo = propuesta
            self.lbl_perfil.setText(f"Se aplicó tu formato guardado «{nombre_perfil}»."
                                    if nombre_perfil else "")
        self._llenar_combos()
        self._actualizar_vista()

    def _llenar_combos(self):
        for clave, combo in self._combos.items():
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("— esta columna no existe —", None)
            for normal, texto in self._textos.items():
                combo.addItem(texto, normal)
            combo.setCurrentIndex(max(combo.findData(self.estado.mapeo.get(clave)), 0))
            combo.blockSignals(False)

    # ── Mostrar ejemplos ───────────────────────────────────────────────────────

    def _leer_combos(self) -> dict[str, str]:
        return {clave: combo.currentData() for clave, combo in self._combos.items()
                if combo.currentData() is not None}

    def _cambio_de_columna(self):
        self.estado.mapeo = self._leer_combos()
        self.lbl_perfil.setText("")
        self._actualizar_vista()

    def _actualizar_vista(self):
        mapeo = self._leer_combos()
        for clave, ejemplo in self._ejemplos.items():
            posicion = self._posiciones.get(mapeo.get(clave))
            valores = [] if posicion is None else [
                limpiar(f[posicion]) for f in self._filas_datos if posicion < len(f)]
            distintos = dict.fromkeys(v[:18] for v in valores if v)       # sin repetir, en orden
            texto = ", ".join(distintos)[:50]
            ejemplo.setText(f"Ej.: {texto}" if texto else "")

        sin_usar = mapeo_mod.columnas_sin_usar(self._encabezados, mapeo)
        self.lbl_sin_usar.setText("Columnas que NO se importarán: " + ", ".join(sin_usar) + "."
                                  if sin_usar else "")
        self._llenar_tabla()

    def _llenar_tabla(self):
        filas = self._filas_datos[:FILAS_DE_EJEMPLO]
        self.tabla.clear()
        self.tabla.setColumnCount(len(self._encabezados))
        self.tabla.setRowCount(len(filas))
        self.tabla.setHorizontalHeaderLabels([str(h or "").strip() for h in self._encabezados])
        for r, celdas in enumerate(filas):
            for c in range(len(self._encabezados)):
                valor = limpiar(celdas[c]) if c < len(celdas) else None
                self.tabla.setItem(r, c, QTableWidgetItem(valor or ""))
        self.tabla.resizeColumnsToContents()

    # ── Formatos guardados ─────────────────────────────────────────────────────

    def _guardar_formato(self):
        mapeo = self._leer_combos()
        if not mapeo:
            self.avisar("Primero asigna al menos una columna.")
            return
        nombre, aceptado = QInputDialog.getText(
            self, "Guardar formato", "Nombre del formato (por ejemplo, «Laboratorio de Física»):")
        if not aceptado or not nombre.strip():
            return
        try:
            perfiles.guardar(nombre, mapeo)
        except ValueError as e:
            self.avisar(str(e))
            return
        QMessageBox.information(self, "Formato guardado",
                                "Listo. La próxima vez que subas un archivo con estas columnas, "
                                "se aplicará solo.")

    # ── Salir del paso ─────────────────────────────────────────────────────────

    def validar(self) -> bool:
        mapeo = self._leer_combos()
        faltan = mapeo_mod.campos_faltantes(mapeo)
        if faltan:
            return self.avisar("Falta indicar la columna de: " + ", ".join(faltan) + ".")

        valores = list(mapeo.values())
        repetida = next((v for v in valores if valores.count(v) > 1), None)
        if repetida:
            return self.avisar(f"La columna «{self._textos[repetida]}» está elegida para más de un "
                               "dato. Cada dato necesita su propia columna.")

        self.estado.mapeo = mapeo
        self.estado.fila_encabezado = self.spin_fila.value() or None
        return True
