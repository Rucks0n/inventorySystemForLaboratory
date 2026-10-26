"""
app/ui/importar/paso_archivo.py
-------------------------------
Paso 1: elegir el archivo y marcar qué hojas se importan.

El archivo se lee en segundo plano (hilos.TrabajoInspeccion) porque abrir un Excel
grande puede tardar varios segundos.
"""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
)

from app.services.importador.catalogo import cargar_catalogo
from app.services.importador.lector import FORMATOS_ACEPTADOS, fila_vacia
from app.services.importador.mapeo import detectar_fila_encabezado
from app.services.importador.plantilla import crear_plantilla
from app.ui.importar.base import (
    ESTILO_PRIMARIO, ESTILO_SECUNDARIO, Paso, detener, elegir_destino_xlsx,
    mensaje_de_error_de_archivo,
)
from app.ui.importar.hilos import TrabajoInspeccion


class PasoArchivo(Paso):
    titulo = "Archivo"
    ayuda = (f"Elige el archivo con tu inventario ({FORMATOS_ACEPTADOS}). Si todavía no lo tienes "
             "armado, descarga la plantilla, llénala y súbela.")

    def __init__(self, estado):
        super().__init__(estado)
        self._trabajo = None

        fila = QHBoxLayout()
        self.btn_elegir = QPushButton("📂  Elegir archivo…")
        self.btn_elegir.setFixedHeight(36)
        self.btn_elegir.setStyleSheet(ESTILO_PRIMARIO)
        self.btn_elegir.clicked.connect(self._elegir)
        self.btn_plantilla = QPushButton("⬇  Descargar plantilla")
        self.btn_plantilla.setFixedHeight(36)
        self.btn_plantilla.setStyleSheet(ESTILO_SECUNDARIO)
        self.btn_plantilla.clicked.connect(self._descargar_plantilla)
        fila.addWidget(self.btn_elegir)
        fila.addWidget(self.btn_plantilla)
        fila.addStretch()
        self.cuerpo.addLayout(fila)

        self.lbl_ruta = QLabel("Ningún archivo elegido.")
        self.lbl_ruta.setStyleSheet("font-weight:bold;")
        self.lbl_ruta.setWordWrap(True)
        self.cuerpo.addWidget(self.lbl_ruta)

        self.lbl_estado = QLabel("")
        self.lbl_estado.setWordWrap(True)
        self.cuerpo.addWidget(self.lbl_estado)

        self.lista = QListWidget()
        self.lista.setAlternatingRowColors(True)
        self.cuerpo.addWidget(self.lista, 1)

        self.actualizar_botones(puede_seguir=False)

    # ── Elegir y leer el archivo ───────────────────────────────────────────────

    def _elegir(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Elegir inventario", "",
            "Inventarios (*.xlsx *.xlsm *.csv);;Todos los archivos (*)")
        if ruta:
            self.abrir(ruta)

    def abrir(self, ruta: str):
        """Empieza a leer el archivo (también lo usan las pruebas)."""
        detener(self._trabajo)
        self.estado.reiniciar()
        self.estado.ruta = ruta
        self.lista.clear()
        self.lbl_ruta.setText(os.path.basename(ruta))
        self.lbl_estado.setText("Leyendo el archivo… (si es muy grande, puede tardar unos segundos)")
        self.btn_elegir.setEnabled(False)
        self.actualizar_botones(puede_seguir=False)

        self._trabajo = TrabajoInspeccion(ruta)
        self._trabajo.listo.connect(self._mostrar_hojas)
        self._trabajo.error.connect(self._fallo)
        self._trabajo.start()

    def _fallo(self, mensaje: str):
        self.btn_elegir.setEnabled(True)
        self.estado.reiniciar()
        self.lbl_ruta.setText("Ningún archivo elegido.")
        self.lbl_estado.setText("")
        QMessageBox.warning(self, "No se pudo leer el archivo", mensaje)

    def _mostrar_hojas(self, hojas, previas):
        self.btn_elegir.setEnabled(True)
        self.estado.hojas, self.estado.previas = hojas, previas

        parecen_inventario = {h.nombre: detectar_fila_encabezado(previas[h.nombre]) is not None
                              for h in hojas}
        alguna = any(parecen_inventario.values())
        for hoja in hojas:
            vacia = all(fila_vacia(f) for f in previas[hoja.nombre])
            notas = []
            if not hoja.visible:
                notas.append("oculta")
            if vacia:
                notas.append("vacía")
            elif alguna and not parecen_inventario[hoja.nombre]:
                notas.append("no parece un inventario")
            marcada = hoja.visible and not vacia and (parecen_inventario[hoja.nombre] or not alguna)

            item = QListWidgetItem(hoja.nombre + (f"   ({', '.join(notas)})" if notas else ""))
            item.setData(Qt.ItemDataRole.UserRole, hoja.nombre)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if marcada else Qt.CheckState.Unchecked)
            self.lista.addItem(item)

        self.lbl_estado.setText(
            f"El archivo tiene {len(hojas)} hoja(s). Marca las que quieres importar:"
            if len(hojas) > 1 else "Se leerá esta hoja (marcada abajo):")
        self.actualizar_botones(puede_seguir=True)

    # ── Plantilla ──────────────────────────────────────────────────────────────

    def _descargar_plantilla(self):
        ruta = elegir_destino_xlsx(self, "Guardar plantilla", "plantilla_inventario.xlsx")
        if not ruta:
            return
        try:
            crear_plantilla(ruta, cargar_catalogo().nombres_de_tipos())
        except OSError as e:
            QMessageBox.warning(self, "No se pudo guardar", mensaje_de_error_de_archivo(e))
            return
        QMessageBox.information(self, "Plantilla guardada",
                                f"Listo. La plantilla quedó en:\n{ruta}")

    # ── Paso ───────────────────────────────────────────────────────────────────

    def al_salir(self):
        detener(self._trabajo)

    def validar(self) -> bool:
        elegidas = [self.lista.item(i).data(Qt.ItemDataRole.UserRole)
                    for i in range(self.lista.count())
                    if self.lista.item(i).checkState() == Qt.CheckState.Checked]
        if not elegidas:
            return self.avisar("Elige un archivo y marca al menos una hoja para importar.")
        self.estado.hojas_elegidas = elegidas
        return True
