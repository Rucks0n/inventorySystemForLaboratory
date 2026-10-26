"""
app/services/importador/ejecutor.py
-----------------------------------
Guarda en la base de datos las filas que el analizador dio por buenas.

Garantías (esto es lo que protege la integridad de tus datos):
  1. ANTES de tocar nada se crea una copia de seguridad (db/respaldos/).
  2. TODO se guarda en UNA sola transacción: o se guarda completo, o no se
     guarda nada. Si algo falla o el usuario cancela, la base queda exactamente
     como estaba.
  3. Lo que ya existe nunca se borra, ni se pisa con celdas vacías.
  4. Se puede repetir sin miedo: con "omitir", volver a subir el mismo archivo
     no duplica nada.

Cómo se sabe si un ítem YA EXISTE: mismo depósito + mismo nombre + misma
referencia (comparando sin mayúsculas, tildes ni espacios de más).

Funciones:
    simular(analisis, politica)   → Plan (vista previa; NO guarda nada)
    ejecutar(analisis, politica)  → Resultado (guarda)
"""

import sqlite3

from app.services.importador.catalogo import Catalogo, cargar_catalogo
from app.services.importador.modelos import (
    Analisis, ErrorImportacion, FilaValida, ImportacionCancelada, Incidencia, Plan, Resultado,
)
from app.services.importador.texto import clave, normalizar
from app.utils.logger import log
from config.constants import IMP_DUP_OMITIR, IMP_ERROR
from db.database import obtener_conexion
from db.respaldos import crear_respaldo

TAMANO_LOTE = 1000

_INSERTAR = """
    INSERT INTO items (deposito_id, nombre, referencia, cantidad_total, cantidad_disp,
                       ubicacion, observaciones, tipo_id, unidad)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""
# COALESCE: si el archivo trae la celda vacía, se conserva lo que ya había
_ACTUALIZAR = """
    UPDATE items SET
        cantidad_total = ?,
        cantidad_disp  = ? - cantidad_prest,
        ubicacion      = COALESCE(?, ubicacion),
        observaciones  = COALESCE(?, observaciones),
        tipo_id        = COALESCE(?, tipo_id),
        unidad         = COALESCE(?, unidad)
    WHERE id = ?
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Vista previa
# ─────────────────────────────────────────────────────────────────────────────

def simular(analisis: Analisis, politica: str) -> Plan:
    """Dice qué pasaría al importar (cuántos se crean, actualizan u omiten) sin guardar nada."""
    conn = obtener_conexion()
    try:
        catalogo = cargar_catalogo(conn)
        plan = planificar(conn, analisis, politica, catalogo)
        plan.depositos_nuevos = [n for n in analisis.depositos_nuevos if clave(n) not in catalogo.depositos]
        return plan
    finally:
        conn.close()


def planificar(conn, analisis: Analisis, politica: str, catalogo: Catalogo) -> Plan:
    """Compara cada fila válida con lo que ya hay en la base y decide qué hacer con ella."""
    plan = Plan()
    id_deposito = {clave(f.deposito): catalogo.depositos[clave(f.deposito)][0]
                   for f in analisis.filas if clave(f.deposito) in catalogo.depositos}
    existentes = _items_existentes(conn, set(id_deposito.values()))

    for fila in analisis.filas:
        deposito_id = id_deposito.get(clave(fila.deposito))        # None = depósito nuevo
        candidatos = existentes.get(
            (deposito_id, normalizar(fila.nombre), normalizar(fila.referencia)), []
        ) if deposito_id else []

        if not candidatos:
            plan.crear.append(fila)
        elif politica == IMP_DUP_OMITIR:
            plan.omitir.append(fila)
        elif len(candidatos) > 1:
            plan.conflictos.append(_conflicto(
                fila, f"«{fila.nombre}»: hay {len(candidatos)} ítems iguales en la base; "
                      "no se sabe cuál actualizar."))
        else:
            item = candidatos[0]
            motivo = _motivo_de_conflicto(item, fila, catalogo)
            if motivo:
                plan.conflictos.append(_conflicto(fila, motivo))
            elif _hay_cambios(item, fila):
                plan.actualizar.append((item["id"], fila))
            else:
                plan.omitir.append(fila)                           # igual a lo que ya había
    return plan


# ─────────────────────────────────────────────────────────────────────────────
#  Importación
# ─────────────────────────────────────────────────────────────────────────────

def ejecutar(analisis: Analisis, politica: str, progreso=None, cancelado=None) -> Resultado:
    """
    Guarda la importación. Si algo falla o se cancela, NO queda nada guardado.

    progreso(mensaje, hecho, total) — para la barra de avance (opcional)
    cancelado() → True si el usuario canceló (opcional)

    Lanza ErrorImportacion (algo falló; la base quedó como estaba) o
    ImportacionCancelada (el usuario canceló; la base quedó como estaba).
    """
    if not analisis.filas:
        raise ErrorImportacion("No hay ninguna fila válida para importar.")

    respaldo = crear_respaldo("antes_de_importar")
    conn = obtener_conexion()
    try:
        conn.execute("BEGIN")
        catalogo = cargar_catalogo(conn)
        depositos_creados = _crear_depositos_faltantes(conn, analisis, catalogo)
        plan = planificar(conn, analisis, politica, catalogo)

        total, hecho = len(plan.crear) + len(plan.actualizar), 0
        for lote in _lotes(plan.crear):
            _comprobar_cancelacion(cancelado)
            conn.executemany(_INSERTAR, [_valores_nuevo(f, catalogo, analisis) for f in lote])
            hecho += len(lote)
            _avisar(progreso, hecho, total)
        for lote in _lotes(plan.actualizar):
            _comprobar_cancelacion(cancelado)
            conn.executemany(_ACTUALIZAR, [
                (f.cantidad, f.cantidad, f.ubicacion, f.observaciones, f.tipo_id, f.unidad, item_id)
                for item_id, f in lote])
            hecho += len(lote)
            _avisar(progreso, hecho, total)

        _comprobar_cancelacion(cancelado)
        conn.commit()
    except ImportacionCancelada:
        conn.rollback()
        log.info("Importación cancelada por el usuario. La base no cambió.")
        raise
    except sqlite3.Error as e:
        conn.rollback()
        log.error(f"Importación fallida (se deshizo todo): {e}")
        raise ErrorImportacion("No se guardó nada: ocurrió un error en la base de datos "
                               f"({e}). Tu inventario quedó como estaba.") from e
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    log.info(f"Importación terminada: {len(plan.crear)} creados, {len(plan.actualizar)} "
             f"actualizados, {len(plan.omitir)} omitidos, {len(plan.conflictos)} con conflicto, "
             f"{len(depositos_creados)} depósitos nuevos.")
    return Resultado(creados=len(plan.crear), actualizados=len(plan.actualizar),
                     omitidos=len(plan.omitir), conflictos=plan.conflictos,
                     depositos_creados=depositos_creados, respaldo=respaldo)


# ─────────────────────────────────────────────────────────────────────────────
#  Internos
# ─────────────────────────────────────────────────────────────────────────────

def _crear_depositos_faltantes(conn, analisis: Analisis, catalogo: Catalogo) -> list[str]:
    """Crea los depósitos nuevos que el análisis pidió (y que nadie creó mientras tanto)."""
    creados = []
    for nombre in analisis.depositos_nuevos:
        if clave(nombre) in catalogo.depositos:
            continue
        cursor = conn.execute("INSERT INTO depositos (nombre) VALUES (?)", (nombre,))
        catalogo.depositos[clave(nombre)] = (cursor.lastrowid, nombre)
        creados.append(nombre)
    return creados


def _items_existentes(conn, ids_deposito: set[int]) -> dict[tuple, list]:
    """Ítems ya guardados en esos depósitos, indexados por (depósito, nombre, referencia)."""
    indice: dict[tuple, list] = {}
    ids = sorted(ids_deposito)
    for i in range(0, len(ids), 500):
        parte = ids[i:i + 500]
        filas = conn.execute(f"""
            SELECT id, deposito_id, nombre, referencia, cantidad_total, cantidad_prest,
                   ubicacion, observaciones, tipo_id, unidad
            FROM items WHERE deposito_id IN ({','.join('?' * len(parte))})
        """, parte)
        for f in filas:
            llave = (f["deposito_id"], normalizar(f["nombre"]), normalizar(f["referencia"]))
            indice.setdefault(llave, []).append(f)
    return indice


def _hay_cambios(item, fila: FilaValida) -> bool:
    """¿El archivo trae algo distinto a lo guardado? Las celdas vacías no cuentan."""
    if fila.cantidad != item["cantidad_total"]:
        return True
    return any(nuevo is not None and nuevo != item[columna] for nuevo, columna in (
        (fila.ubicacion, "ubicacion"), (fila.observaciones, "observaciones"),
        (fila.tipo_id, "tipo_id"), (fila.unidad, "unidad")))


def _motivo_de_conflicto(item, fila: FilaValida, catalogo: Catalogo) -> str | None:
    """Razones por las que NO es seguro actualizar este ítem."""
    if fila.cantidad < item["cantidad_prest"]:
        return (f"«{fila.nombre}»: la cantidad del archivo ({fila.cantidad}) es menor que la que "
                f"está prestada ({item['cantidad_prest']}). Registra primero las devoluciones.")
    if fila.tipo_id and fila.tipo_id != item["tipo_id"] and item["cantidad_prest"] > 0:
        nuevo = catalogo.tipos_por_id.get(fila.tipo_id)
        actual = catalogo.tipos_por_id.get(item["tipo_id"])
        if nuevo and actual and nuevo.comportamiento != actual.comportamiento:
            return (f"«{fila.nombre}»: no se puede cambiar de «{actual.nombre}» a «{nuevo.nombre}» "
                    "mientras haya unidades prestadas.")
    return None


def _conflicto(fila: FilaValida, mensaje: str) -> Incidencia:
    return Incidencia(fila.hoja, fila.fila, IMP_ERROR, None, mensaje)


def _valores_nuevo(fila: FilaValida, catalogo: Catalogo, analisis: Analisis) -> tuple:
    deposito_id = catalogo.depositos[clave(fila.deposito)][0]
    tipo_id = fila.tipo_id or analisis.config.tipo_defecto_id      # el tipo por defecto solo vale al crear
    return (deposito_id, fila.nombre, fila.referencia, fila.cantidad, fila.cantidad,
            fila.ubicacion, fila.observaciones, tipo_id, fila.unidad)


def _lotes(elementos: list):
    for i in range(0, len(elementos), TAMANO_LOTE):
        yield elementos[i:i + TAMANO_LOTE]


def _comprobar_cancelacion(cancelado):
    if cancelado and cancelado():
        raise ImportacionCancelada()


def _avisar(progreso, hecho: int, total: int):
    if progreso:
        progreso("Guardando ítems…", hecho, total)
