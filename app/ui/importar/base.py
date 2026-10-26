"""
app/ui/importar/base.py
-----------------------
Piezas comunes del asistente de importación:

  EstadoAsistente   lo que el usuario va decidiendo; lo comparten todos los pasos.
  Paso              clase base de cada pantalla del asistente.

Para agregar un paso nuevo: crea una clase que herede de Paso (mira paso_destino.py
como ejemplo sencillo) y añádela a la lista de pasos en dialogo.py.
"""

from dataclasses import dataclass, field

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QLabel, QMessageBox, QVBoxLayout, QWidget

from app.services.importador.modelos import Analisis, ConfigImportacion, Plan, Resultado
from config.constants import IMP_DEPOSITO_POR_HOJA, IMP_DUP_OMITIR

# Mismos colores de botones que el resto de la aplicación
ESTILO_PRIMARIO = ("QPushButton{background:#2E5090;color:white;border-radius:4px;padding:0 14px;"
                   "font-size:13px;}QPushButton:hover{background:#3A63B0;}"
                   "QPushButton:disabled{background:#AAB4CC;}")
ESTILO_SECUNDARIO = ("QPushButton{background:#EEE;color:#333;border-radius:4px;border:1px solid #CCC;"
                     "padding:0 14px;font-size:13px;}QPushButton:hover{background:#DDD;}"
                     "QPushButton:disabled{color:#AAA;}")


def miles(numero: int) -> str:
    """12345 → '12.345' (así se escriben los miles en español)."""
    return f"{numero:,}".replace(",", ".")


def detener(trabajo) -> None:
    """Cancela un trabajo en segundo plano (si sigue corriendo) y espera a que termine."""
    if trabajo is not None and trabajo.isRunning():
        trabajo.cancelar()
        trabajo.wait()


def elegir_destino_xlsx(padre: QWidget, titulo: str, nombre_sugerido: str) -> str | None:
    """Pide dónde guardar un .xlsx. Retorna la ruta (con extensión) o None si se cancela."""
    ruta, _ = QFileDialog.getSaveFileName(padre, titulo, nombre_sugerido, "Excel (*.xlsx)")
    if not ruta:
        return None
    return ruta if ruta.lower().endswith(".xlsx") else ruta + ".xlsx"


def mensaje_de_error_de_archivo(error: OSError) -> str:
    """Explica en palabras simples por qué no se pudo escribir un archivo."""
    if isinstance(error, PermissionError):
        return ("No se pudo guardar el archivo. Si ya existe y está abierto en Excel, ciérralo; "
                "también puedes elegir otra carpeta.")
    return f"No se pudo guardar el archivo: {error.strerror or error}"


@dataclass
class EstadoAsistente:
    """Todo lo que el usuario ha decidido hasta ahora."""
    # Paso 1: archivo
    ruta: str = ""
    hojas: list = field(default_factory=list)                  # list[HojaInfo]
    previas: dict = field(default_factory=dict)                # hoja → primeras filas (ejemplos)
    hojas_elegidas: list[str] = field(default_factory=list)
    # Paso 2: columnas
    fila_encabezado: int | None = None                         # None = detectarla sola
    mapeo: dict[str, str] = field(default_factory=dict)
    # Paso 3: depósitos y opciones
    modo_deposito: str = IMP_DEPOSITO_POR_HOJA
    deposito_unico: str | None = None
    crear_depositos: bool = False
    tipo_defecto_id: int | None = None
    politica: str = IMP_DUP_OMITIR
    # Resultados de los pasos 4 y 5
    analisis: Analisis | None = None
    plan: Plan | None = None
    resultado: Resultado | None = None

    def reiniciar(self):
        """Olvida todo (se usa al elegir otro archivo)."""
        for nombre, valor in EstadoAsistente().__dict__.items():
            setattr(self, nombre, valor)

    def config(self) -> ConfigImportacion:
        return ConfigImportacion(
            ruta=self.ruta, hojas=list(self.hojas_elegidas), mapeo=dict(self.mapeo),
            fila_encabezado=self.fila_encabezado, modo_deposito=self.modo_deposito,
            deposito_unico=self.deposito_unico, crear_depositos=self.crear_depositos,
            tipo_defecto_id=self.tipo_defecto_id,
        )


class Paso(QWidget):
    """
    Una pantalla del asistente.

    Lo que puede redefinir cada paso:
        al_entrar()        se llama al llegar al paso (cargar datos, lanzar un trabajo…)
        al_salir()         se llama al irse (cancelar trabajos pendientes)
        validar() -> bool  ¿se puede avanzar? Si no, avisa al usuario y retorna False
        confirmar_cierre() -> bool   ¿se puede cerrar el asistente ahora?

    Para cambiar los botones de abajo, el paso modifica estos atributos y llama a
    self.cambio.emit():
        texto_siguiente, puede_seguir, puede_volver, es_ultimo, terminado
    """
    titulo = ""
    ayuda = ""
    cambio = pyqtSignal()

    def __init__(self, estado: EstadoAsistente):
        super().__init__()
        self.estado = estado
        self.texto_siguiente = "Siguiente  ›"
        self.puede_seguir = True
        self.puede_volver = True
        self.es_ultimo = False          # el último paso no tiene botón «Siguiente»
        self.terminado = False          # True: el botón «Cancelar» pasa a decir «Cerrar»

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(10)
        if self.ayuda:
            lbl = QLabel(self.ayuda)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color:#555;font-size:13px;")
            raiz.addWidget(lbl)
        self.cuerpo = QVBoxLayout()           # los pasos agregan aquí sus widgets
        self.cuerpo.setSpacing(10)
        raiz.addLayout(self.cuerpo, 1)

    def al_entrar(self):
        pass

    def al_salir(self):
        pass

    def validar(self) -> bool:
        return True

    def confirmar_cierre(self) -> bool:
        return True

    def avisar(self, texto: str) -> bool:
        """Muestra un aviso y retorna False (para escribir: return self.avisar("..."))."""
        QMessageBox.warning(self, "Revisa este paso", texto)
        return False

    def actualizar_botones(self, **cambios):
        """Cambia atributos de los botones (texto_siguiente=…, puede_seguir=…) y avisa al diálogo."""
        for nombre, valor in cambios.items():
            setattr(self, nombre, valor)
        self.cambio.emit()
