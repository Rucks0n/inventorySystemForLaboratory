"""
app/services/importador/modelos.py
----------------------------------
Los "paquetes de datos" que se pasan de una pieza a otra del importador.
Aquí no hay lógica: solo se define qué información lleva cada paquete.
"""

from dataclasses import dataclass, field

from config.constants import IMP_DEPOSITO_POR_HOJA, IMP_ERROR


class ErrorImportacion(Exception):
    """Problema que se le puede mostrar al usuario tal cual (el mensaje ya es claro)."""


class ImportacionCancelada(Exception):
    """El usuario canceló mientras se leía o se guardaba."""


@dataclass
class ConfigImportacion:
    """Todo lo que el usuario decidió en el asistente."""
    ruta: str
    hojas: list[str]                          # hojas que se van a importar
    mapeo: dict[str, str]                     # campo → encabezado normalizado de la columna
    fila_encabezado: int | None = None        # None = detectarla en cada hoja
    modo_deposito: str = IMP_DEPOSITO_POR_HOJA
    deposito_unico: str | None = None         # solo si modo_deposito == IMP_DEPOSITO_UNICO
    crear_depositos: bool = False             # permitir crear los depósitos que falten
    tipo_defecto_id: int | None = None        # tipo para las filas que no traen tipo


@dataclass
class Incidencia:
    """Un problema (o aviso) encontrado en el archivo."""
    hoja: str
    fila: int                  # número de fila en el Excel; 0 = problema de la hoja completa
    nivel: str                 # IMP_ERROR (no se importa) o IMP_AVISO (se importa, revisar)
    campo: str | None
    mensaje: str


@dataclass
class FilaValida:
    """Una fila que pasó todas las revisiones y está lista para guardarse."""
    hoja: str
    fila: int
    deposito: str
    nombre: str
    cantidad: int
    referencia: str | None = None
    ubicacion: str | None = None
    observaciones: str | None = None
    tipo_id: int | None = None      # solo si el archivo traía el tipo de esa fila
    unidad: str | None = None


@dataclass
class Analisis:
    """Resultado de revisar el archivo completo (todavía no se guardó nada)."""
    config: ConfigImportacion
    filas: list[FilaValida] = field(default_factory=list)
    incidencias: list[Incidencia] = field(default_factory=list)
    originales: dict[tuple[str, int], list] = field(default_factory=dict)   # (hoja, fila) → celdas
    encabezados: dict[str, list[str]] = field(default_factory=dict)         # hoja → encabezados
    depositos_nuevos: list[str] = field(default_factory=list)
    leidas: int = 0

    @property
    def filas_con_error(self) -> int:
        """Cuántas filas distintas NO se importarán por tener algún error."""
        return len({(i.hoja, i.fila) for i in self.incidencias
                    if i.nivel == IMP_ERROR and i.fila > 0})

    @property
    def hojas_omitidas(self) -> int:
        """Hojas que no se pudieron leer (problema de la hoja completa)."""
        return len({i.hoja for i in self.incidencias if i.fila == 0 and i.nivel == IMP_ERROR})


@dataclass
class Plan:
    """Qué va a pasar con cada fila válida al compararla con lo que ya hay en la base."""
    crear: list[FilaValida] = field(default_factory=list)
    actualizar: list[tuple[int, FilaValida]] = field(default_factory=list)   # (id del ítem, fila)
    omitir: list[FilaValida] = field(default_factory=list)                   # ya existía
    conflictos: list[Incidencia] = field(default_factory=list)
    depositos_nuevos: list[str] = field(default_factory=list)


@dataclass
class Resultado:
    """Lo que realmente se guardó."""
    creados: int
    actualizados: int
    omitidos: int
    conflictos: list[Incidencia]
    depositos_creados: list[str]
    respaldo: str | None
