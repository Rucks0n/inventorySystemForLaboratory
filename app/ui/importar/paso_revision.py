"""
app/ui/importar/paso_revision.py
--------------------------------
Paso 4: revisar TODO el archivo antes de guardar nada.

Muestra cuántos ítems se crearán, cuántos ya existen y qué filas tienen problemas
(con el motivo y el número de fila para corregirlas en el Excel). El reporte completo
de problemas se puede descargar como Excel.
"""

from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QHeaderView, QLabel, QMessageBox, QProgressBar, QPushButton, QStackedWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.services.importador.reporte_errores import escribir_reporte
from app.ui.importar.base import (
    ESTILO_SECUNDARIO, Paso, detener, elegir_destino_xlsx, mensaje_de_error_de_archivo, miles,
)
from app.ui.importar.hilos import TrabajoAnalisis
from config.constants import IMP_AVISO, IMP_ERROR

MAX_PROBLEMAS_EN_TABLA = 500          # el reporte en Excel trae todos


class PasoRevision(Paso):
    titulo = "Revisión"
    ayuda = "Se revisa todo el archivo ANTES de guardar. Por ahora no se ha cambiado nada en tu inventario."

    def __init__(self, estado):
        super().__init__(estado)
        self._trabajo = None

        self.pila = QStackedWidget()
        self.cuerpo.addWidget(self.pila, 1)

        # Página 0: leyendo
        espera = QWidget()
        capa = QVBoxLayout(espera)
        capa.addStretch()
        self.lbl_progreso = QLabel("Leyendo el archivo…")
        self.lbl_progreso.setStyleSheet("font-size:14px;")
        barra = QProgressBar()
        barra.setRange(0, 0)                 # barra "ocupado": no sabemos cuántas filas hay
        barra.setTextVisible(False)
        capa.addWidget(self.lbl_progreso)
        capa.addWidget(barra)
        capa.addStretch()
        self.pila.addWidget(espera)

        # Página 1: resultado de la revisión
        listo = QWidget()
        capa = QVBoxLayout(listo)
        capa.setContentsMargins(0, 0, 0, 0)
        self.lbl_resumen = QLabel("")
        self.lbl_resumen.setWordWrap(True)
        self.lbl_resumen.setStyleSheet("font-size:13px;")
        capa.addWidget(self.lbl_resumen)

        self.lbl_tabla = QLabel("")
        self.lbl_tabla.setStyleSheet("color:#777;")
        capa.addWidget(self.lbl_tabla)
        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(["Hoja", "Fila", "Gravedad", "Qué pasa"])
        self.tabla.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setWordWrap(True)
        capa.addWidget(self.tabla, 1)

        self.btn_reporte = QPushButton("⬇  Descargar reporte de problemas (Excel)")
        self.btn_reporte.setFixedHeight(34)
        self.btn_reporte.setStyleSheet(ESTILO_SECUNDARIO)
        self.btn_reporte.clicked.connect(self._descargar_reporte)
        capa.addWidget(self.btn_reporte)
        self.pila.addWidget(listo)

    # ── Revisar ────────────────────────────────────────────────────────────────

    def al_entrar(self):
        detener(self._trabajo)
        self.estado.analisis = self.estado.plan = None
        self.pila.setCurrentIndex(0)
        self.lbl_progreso.setText("Leyendo el archivo…")
        self.actualizar_botones(puede_seguir=False, texto_siguiente="Importar  ›")

        self._trabajo = TrabajoAnalisis(self.estado.config(), self.estado.politica)
        self._trabajo.progreso.connect(
            lambda mensaje, leidas: self.lbl_progreso.setText(f"{mensaje}   {miles(leidas)} filas leídas"))
        self._trabajo.listo.connect(self._mostrar_resultado)
        self._trabajo.error.connect(self._fallo)
        self._trabajo.start()

    def al_salir(self):
        detener(self._trabajo)

    def _fallo(self, mensaje: str):
        self.pila.setCurrentIndex(1)
        self.lbl_resumen.setText(f"<b>No se pudo revisar el archivo.</b><br>{mensaje}")
        self.lbl_tabla.setText("")
        self.tabla.setRowCount(0)
        self.btn_reporte.setVisible(False)
        self.actualizar_botones(puede_seguir=False)

    def _mostrar_resultado(self, analisis, plan):
        self.estado.analisis, self.estado.plan = analisis, plan
        validas = len(analisis.filas)
        con_error = analisis.filas_con_error
        hacer = len(plan.crear) + len(plan.actualizar)
        problemas = sorted(list(analisis.incidencias) + list(plan.conflictos),
                           key=lambda p: p.nivel != IMP_ERROR)     # primero los errores
        avisos = sum(1 for p in problemas if p.nivel == IMP_AVISO)

        lineas = [f"Se leyeron <b>{miles(analisis.leidas)}</b> filas de {len(analisis.config.hojas)} hoja(s)."]
        if validas:
            lineas.append(f"✔ <b>{miles(validas)}</b> filas correctas: se crean <b>{miles(len(plan.crear))}</b>, "
                          f"se actualizan <b>{miles(len(plan.actualizar))}</b> y "
                          f"<b>{miles(len(plan.omitir))}</b> ya existían (se dejan igual).")
        if plan.depositos_nuevos:
            lineas.append("＋ Se crearán los depósitos: " + ", ".join(plan.depositos_nuevos) + ".")
        if con_error:
            lineas.append(f"✘ <b>{miles(con_error)}</b> filas tienen errores y <b>no se importarán</b>.")
        if analisis.hojas_omitidas:
            lineas.append(f"✘ <b>{analisis.hojas_omitidas}</b> hoja(s) no se pudieron importar.")
        if plan.conflictos:
            lineas.append(f"✘ <b>{miles(len(plan.conflictos))}</b> ítems no se pueden actualizar sin riesgo.")
        if avisos:
            lineas.append(f"⚠ {miles(avisos)} aviso(s): se importan, pero conviene revisarlos.")
        if not validas:
            lineas.append("<b>No hay ninguna fila correcta.</b> Corrige el archivo (el reporte te dice qué) "
                          "o vuelve atrás y cambia las columnas.")
        elif not hacer:
            lineas.append("<b>No hay nada nuevo que importar:</b> todo lo del archivo ya existe en el inventario.")
        self.lbl_resumen.setText("<br>".join(lineas))

        self._llenar_tabla(problemas)
        self.btn_reporte.setVisible(bool(problemas))
        self.pila.setCurrentIndex(1)

        if hacer:
            texto = (f"Importar solo lo correcto ({miles(hacer)})  ›" if con_error or analisis.hojas_omitidas
                     else f"Importar {miles(hacer)} ítems  ›")
        else:
            texto = "Importar  ›"
        self.actualizar_botones(puede_seguir=hacer > 0, texto_siguiente=texto)

    def _llenar_tabla(self, problemas):
        mostrar = problemas[:MAX_PROBLEMAS_EN_TABLA]
        self.lbl_tabla.setText(
            f"Problemas encontrados (se muestran {miles(len(mostrar))} de {miles(len(problemas))}; "
            "descarga el reporte para verlos todos):" if len(problemas) > len(mostrar)
            else "Problemas encontrados:" if problemas else "")
        self.tabla.setRowCount(len(mostrar))
        for fila, p in enumerate(mostrar):
            es_error = p.nivel == IMP_ERROR
            celdas = (p.hoja, str(p.fila) if p.fila else "toda la hoja",
                      "Error" if es_error else "Aviso", p.mensaje)
            for columna, texto in enumerate(celdas):
                item = QTableWidgetItem(texto)
                if columna == 2:
                    item.setForeground(QBrush(QColor("#C0392B" if es_error else "#B9770E")))
                self.tabla.setItem(fila, columna, item)
        self.tabla.resizeColumnsToContents()
        self.tabla.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._ajustar_filas()

    def _ajustar_filas(self):
        """Altura de cada fila según el texto (los mensajes largos se parten en varias líneas)."""
        self.tabla.resizeRowsToContents()

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._ajustar_filas()                    # al cambiar el ancho de la ventana, cambia el ajuste de línea

    # ── Reporte y salida ───────────────────────────────────────────────────────

    def _descargar_reporte(self):
        ruta = elegir_destino_xlsx(self, "Guardar reporte de problemas", "problemas_importacion.xlsx")
        if not ruta:
            return
        try:
            escribir_reporte(ruta, self.estado.analisis, self.estado.plan.conflictos)
        except OSError as e:
            QMessageBox.warning(self, "No se pudo guardar", mensaje_de_error_de_archivo(e))
            return
        QMessageBox.information(self, "Reporte guardado", f"Listo. El reporte quedó en:\n{ruta}")

    def validar(self) -> bool:
        analisis = self.estado.analisis
        if analisis is None:
            return False
        malas = analisis.filas_con_error + len(self.estado.plan.conflictos)
        if malas or analisis.hojas_omitidas:
            respuesta = QMessageBox.question(
                self, "Hay problemas",
                "Hay filas (u hojas) con problemas que NO se importarán.\n"
                "¿Importar solo lo que está correcto? Lo demás puedes corregirlo en el Excel y "
                "volver a subir el archivo completo: lo que ya se importó no se duplica.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            return respuesta == QMessageBox.StandardButton.Yes
        return True
