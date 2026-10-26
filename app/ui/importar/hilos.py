"""
app/ui/importar/hilos.py
---------------------
Trabajos que corren en segundo plano para que la ventana NUNCA se congele
mientras se lee un archivo grande o se guarda un inventario enorme.

Cada trabajo avisa con señales:
    progreso   → cuánto va (para la barra de avance)
    listo      → terminó bien, y entrega el resultado
    error      → falló, con un mensaje que se le puede mostrar al usuario
    cancelado  → el usuario canceló (la base queda como estaba)

La lógica real NO está aquí: está en app/services/importador/. Estos trabajos
solo la llaman en otro hilo.
"""

from PyQt6.QtCore import QThread, pyqtSignal

from app.services.importador import ejecutor
from app.services.importador.analizador import analizar
from app.services.importador.catalogo import cargar_catalogo
from app.services.importador.lector import Archivo
from app.services.importador.modelos import ErrorImportacion, ImportacionCancelada, Plan
from app.utils.logger import log

MAX_FILAS_PREVIA = 60            # filas de cada hoja que se leen para mostrar ejemplos
MAX_HOJAS_PREVIA = 60


class _Trabajo(QThread):
    """Base: captura los errores para que nunca se pierdan dentro del hilo."""
    error     = pyqtSignal(str)
    cancelado = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._cancelar = False

    def cancelar(self):
        self._cancelar = True

    def fue_cancelado(self) -> bool:
        return self._cancelar

    def trabajar(self):                    # lo define cada trabajo
        raise NotImplementedError

    def run(self):
        try:
            self.trabajar()
        except ImportacionCancelada:
            self.cancelado.emit()
        except ErrorImportacion as e:
            self.error.emit(str(e))
        except Exception as e:             # un fallo que no esperábamos: se registra y se explica
            log.error(f"Error inesperado en la importación: {e}", exc_info=True)
            self.error.emit(f"Ocurrió un error inesperado: {e}\nNo se guardó nada.")


class TrabajoInspeccion(_Trabajo):
    """Abre el archivo UNA vez y lee sus hojas y las primeras filas de cada una."""
    listo = pyqtSignal(object, object)     # (hojas, {nombre de hoja: filas de ejemplo})

    def __init__(self, ruta: str):
        super().__init__()
        self.ruta = ruta

    def trabajar(self):
        with Archivo(self.ruta) as archivo:
            hojas = archivo.hojas()[:MAX_HOJAS_PREVIA]
            previas = {h.nombre: archivo.previa(h.nombre, MAX_FILAS_PREVIA) for h in hojas}
        self.listo.emit(hojas, previas)


class TrabajoAnalisis(_Trabajo):
    """Revisa el archivo completo y calcula qué pasaría al importar. No guarda nada."""
    progreso = pyqtSignal(str, int)        # (mensaje, filas leídas)
    listo    = pyqtSignal(object, object)  # (Analisis, Plan)

    def __init__(self, config, politica: str):
        super().__init__()
        self.config, self.politica = config, politica

    def trabajar(self):
        analisis = analizar(
            self.config, cargar_catalogo(),
            progreso=lambda mensaje, hecho, total: self.progreso.emit(mensaje, hecho),
            cancelado=self.fue_cancelado)
        plan = ejecutor.simular(analisis, self.politica) if analisis.filas else Plan()
        self.listo.emit(analisis, plan)


class TrabajoImportacion(_Trabajo):
    """Guarda en la base (con copia de seguridad y en una sola transacción)."""
    progreso = pyqtSignal(int, int)        # (guardados, total)
    listo    = pyqtSignal(object)          # Resultado

    def __init__(self, analisis, politica: str):
        super().__init__()
        self.analisis, self.politica = analisis, politica

    def trabajar(self):
        resultado = ejecutor.ejecutar(
            self.analisis, self.politica,
            progreso=lambda mensaje, hecho, total: self.progreso.emit(hecho, total),
            cancelado=self.fue_cancelado)
        self.listo.emit(resultado)
