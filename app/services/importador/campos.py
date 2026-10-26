"""
app/services/importador/campos.py
---------------------------------
Qué información puede traer un inventario y cómo suelen llamarse sus columnas.

PARA AGREGAR UN NOMBRE DE COLUMNA que el sistema no reconoce (por ejemplo, si un
laboratorio llama "Insumo" a la columna del nombre), solo hay que escribirlo en
la lista `fuertes` del campo correspondiente. No importan las tildes ni las
mayúsculas.

  fuertes → nombres que casi seguro significan ese campo.
  débiles → nombres ambiguos; solo se usan si el campo no se encontró de otra
            forma. Ejemplo: "Descripción" suele ser el nombre del ítem, pero si
            el archivo ya trae una columna "Item", pasa a ser las observaciones.

El PRIMER nombre de `fuertes` es el "canónico": también se reconoce cuando el
encabezado lo contiene como palabra ("Cantidad disponible" → cantidad).

Los campos del sistema son los de la tabla `items`:
    nombre, cantidad (→ cantidad_total), referencia (sirve como código),
    ubicacion, observaciones (sirve como detalles), tipo (→ tipo_id), unidad.
"deposito" no es una columna de `items`, pero puede venir en el archivo.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Campo:
    clave: str                  # nombre interno
    etiqueta: str               # como se le muestra al usuario
    obligatorio: bool
    fuertes: tuple[str, ...]
    debiles: tuple[str, ...] = ()


CAMPOS = (
    Campo("nombre", "Nombre del ítem", True,
          fuertes=("nombre", "item", "nombre del item", "nombre item", "elemento",
                   "articulo", "producto", "material", "equipo", "insumo", "reactivo"),
          debiles=("descripcion", "descripcion del item")),

    Campo("cantidad", "Cantidad", True,
          fuertes=("cantidad", "cant", "cantidad total", "existencias", "stock"),
          debiles=("total", "unidades", "qty")),

    Campo("referencia", "Código o referencia", False,
          fuertes=("referencia", "ref", "codigo", "cod", "placa", "serial", "sku"),
          debiles=("modelo", "numero de inventario", "n inventario", "no inventario")),

    Campo("ubicacion", "Ubicación", False,
          fuertes=("ubicacion", "estante", "lugar", "localizacion", "posicion")),

    Campo("observaciones", "Observaciones / detalles", False,
          fuertes=("observaciones", "observacion", "detalle", "detalles", "notas",
                   "nota", "comentarios", "comentario"),
          debiles=("descripcion",)),

    Campo("tipo", "Tipo (herramienta, consumible…)", False,
          fuertes=("tipo", "categoria", "clase", "tipo de item")),

    Campo("unidad", "Unidad de medida", False,
          fuertes=("unidad", "unidad de medida", "u m", "um", "medida")),

    Campo("deposito", "Depósito", False,
          fuertes=("deposito", "laboratorio", "bodega", "almacen")),
)

CAMPOS_POR_CLAVE = {c.clave: c for c in CAMPOS}

# Para que el usuario sepa qué le falta cuando el archivo no se entiende
OBLIGATORIOS = tuple(c.clave for c in CAMPOS if c.obligatorio)
