"""
app/ui/importar/paso_resultado.py
---------------------------------
Paso 5: guardar en la base de datos y mostrar qué pasó.

Se guarda TODO o NADA (una sola transacción) y antes se hace una copia de seguridad.
Si el usuario cancela o algo falla, el inventario queda exactamente como estaba.
"""

import os

from PyQt6.QtWidgets import QLabel, QMessageBox, QProgressBar

from app.ui.importar.base import Paso, detener, miles
from app.ui.importar.hilos import TrabajoImportacion

MAX_CONFLICTOS_VISIBLES = 10


class PasoResultado(Paso):
    titulo = "Guardando"

    def __init__(self, estado):
        super().__init__(estado)
        self._trabajo = None
        self.es_ultimo = True

        self.lbl_texto = QLabel("")
        self.lbl_texto.setWordWrap(True)
        self.lbl_texto.setStyleSheet("font-size:14px;")
        self.barra = QProgressBar()
        self.cuerpo.addWidget(self.lbl_texto)
        self.cuerpo.addWidget(self.barra)
        self.cuerpo.addStretch()

    # ── Guardar ────────────────────────────────────────────────────────────────

    def al_entrar(self):
        self.estado.resultado = None
        self.lbl_texto.setText("Guardando tu inventario… No cierres el programa.\n"
                               "(Primero se hace una copia de seguridad.)")
        self.barra.setVisible(True)
        self.barra.setRange(0, 0)                   # "ocupado" hasta que lleguen los primeros avances
        self.actualizar_botones(puede_volver=False, terminado=False)

        self._trabajo = TrabajoImportacion(self.estado.analisis, self.estado.politica)
        self._trabajo.progreso.connect(self._avanzar)
        self._trabajo.listo.connect(self._terminado)
        self._trabajo.error.connect(self._fallo)
        self._trabajo.cancelado.connect(self._cancelado)
        self._trabajo.start()

    def _avanzar(self, hecho: int, total: int):
        self.barra.setRange(0, max(total, 1))
        self.barra.setValue(hecho)
        self.lbl_texto.setText(f"Guardando… {miles(hecho)} de {miles(total)} ítems.")

    def _terminado(self, resultado):
        self.estado.resultado = resultado
        lineas = ["<b style='color:#1E8449;font-size:16px;'>✔ Importación terminada</b>", "",
                  f"• Ítems creados: <b>{miles(resultado.creados)}</b>",
                  f"• Ítems actualizados: <b>{miles(resultado.actualizados)}</b>",
                  f"• Ya existían (sin cambios): <b>{miles(resultado.omitidos)}</b>"]
        if resultado.depositos_creados:
            lineas.append("• Depósitos creados: " + ", ".join(resultado.depositos_creados))
        if resultado.conflictos:
            lineas += ["", f"⚠ {miles(len(resultado.conflictos))} ítems no se actualizaron:"]
            lineas += [f"&nbsp;&nbsp;– {c.mensaje}" for c in resultado.conflictos[:MAX_CONFLICTOS_VISIBLES]]
            if len(resultado.conflictos) > MAX_CONFLICTOS_VISIBLES:
                lineas.append("&nbsp;&nbsp;– …")
        if resultado.respaldo:
            lineas += ["", "Antes de importar se guardó una copia de seguridad "
                           f"({os.path.basename(resultado.respaldo)}), por si necesitas volver atrás."]
        self._terminar("<br>".join(lineas), puede_volver=False)

    def _fallo(self, mensaje: str):
        self._terminar(f"<b style='color:#C0392B;'>✘ No se guardó nada.</b><br>{mensaje}", puede_volver=True)

    def _cancelado(self):
        self._terminar("<b>Importación cancelada.</b><br>No se guardó nada: tu inventario quedó "
                       "como estaba.", puede_volver=True)

    def _terminar(self, texto_html: str, puede_volver: bool):
        self.barra.setVisible(False)
        self.lbl_texto.setText(texto_html)
        self.actualizar_botones(puede_volver=puede_volver, terminado=True)

    # ── Salir ──────────────────────────────────────────────────────────────────

    def al_salir(self):
        detener(self._trabajo)

    def confirmar_cierre(self) -> bool:
        if self._trabajo is None or not self._trabajo.isRunning():
            return True
        respuesta = QMessageBox.question(
            self, "Importación en curso",
            "Se está guardando el inventario. Si cancelas ahora, no se guardará nada.\n"
            "¿Cancelar la importación?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        return respuesta == QMessageBox.StandardButton.Yes
