"""
app/services/importador/catalogo.py
-----------------------------------
Lee de la base de datos lo que el importador necesita para validar:
los depósitos que existen y los tipos de ítem.
"""

from dataclasses import dataclass, field

from db.database import obtener_conexion
from app.services.importador.texto import clave, normalizar


@dataclass(frozen=True)
class TipoInfo:
    id: int
    nombre: str
    comportamiento: str          # "presta" o "consume"


@dataclass
class Catalogo:
    depositos: dict[str, tuple[int, str]] = field(default_factory=dict)   # clave → (id, nombre)
    tipos: dict[str, TipoInfo] = field(default_factory=dict)              # nombre normalizado → tipo
    tipos_por_id: dict[int, TipoInfo] = field(default_factory=dict)

    def nombres_de_tipos(self) -> list[str]:
        return [t.nombre for t in self.tipos_por_id.values()]


def cargar_catalogo(conn=None) -> Catalogo:
    """
    Lee depósitos y tipos activos.
    Si no se pasa una conexión, abre una y la cierra al terminar.
    """
    propia = conn is None
    conn = conn or obtener_conexion()
    try:
        cat = Catalogo()
        for f in conn.execute("SELECT id, nombre FROM depositos ORDER BY nombre"):
            cat.depositos[clave(f["nombre"])] = (f["id"], f["nombre"])
        for f in conn.execute(
                "SELECT id, nombre, comportamiento FROM tipos_item WHERE activo = 1 ORDER BY id"):
            tipo = TipoInfo(f["id"], f["nombre"], f["comportamiento"])
            cat.tipos[normalizar(tipo.nombre)] = tipo
            cat.tipos_por_id[tipo.id] = tipo
        return cat
    finally:
        if propia:
            conn.close()
