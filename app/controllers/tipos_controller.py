"""
app/controllers/tipos_controller.py
------------------------------------
Lógica de negocio para los TIPOS de ítem (Herramienta, Consumible, ...).

Cada tipo tiene un comportamiento:
    presta   → se presta y se devuelve
    consume  → se gasta y se descuenta

El administrador puede crear más tipos (ej. "Mobiliario", "Reactivo").
Un tipo que ya tiene ítems no se puede borrar: se desactiva.

Todos los métodos que guardan datos retornan (ok: bool, mensaje: str).
"""

import sqlite3

from db.database          import conexion
from app.utils.logger     import log
from app.utils            import validators
from config.constants     import COMPORTAMIENTOS_VALIDOS, COMP_PRESTA


class TiposController:

    # ── Consultas ──────────────────────────────────────────────────────────

    def obtener_todos(self, solo_activos: bool = True) -> list[dict]:
        """Lista de tipos, con cuántos ítems tiene cada uno (`total_items`)."""
        try:
            with conexion() as conn:
                filtro = "WHERE t.activo = 1" if solo_activos else ""
                filas  = conn.execute(f"""
                    SELECT t.id, t.nombre, t.comportamiento, t.descripcion, t.activo,
                           (SELECT COUNT(*) FROM items i WHERE i.tipo_id = t.id) AS total_items
                    FROM   tipos_item t
                    {filtro}
                    ORDER  BY t.id
                """).fetchall()
                return [dict(f) for f in filas]
        except Exception as e:
            log.error(f"TiposController.obtener_todos: {e}")
            return []

    def obtener_por_id(self, tipo_id: int) -> dict | None:
        for tipo in self.obtener_todos(solo_activos=False):
            if tipo["id"] == tipo_id:
                return tipo
        return None

    def tipo_por_defecto(self) -> dict | None:
        """
        Tipo que se usa cuando no se indica uno: el primero activo que se presta
        (así se conserva el comportamiento de siempre). Si no hay, el primero activo.
        """
        activos = self.obtener_todos(solo_activos=True)
        for tipo in activos:
            if tipo["comportamiento"] == COMP_PRESTA:
                return tipo
        return activos[0] if activos else None

    # ── Altas, cambios y bajas ─────────────────────────────────────────────

    def agregar(self, datos: dict) -> tuple[bool, str]:
        """datos: nombre (obligatorio), comportamiento ('presta'|'consume'), descripcion."""
        ok, msg = self._validar(datos)
        if not ok:
            return False, msg
        try:
            with conexion() as conn:
                conn.execute(
                    "INSERT INTO tipos_item (nombre, comportamiento, descripcion) VALUES (?, ?, ?)",
                    (
                        str(datos["nombre"]).strip(),
                        datos["comportamiento"],
                        str(datos.get("descripcion", "") or "").strip() or None,
                    ),
                )
                conn.commit()
                log.info(f"Tipo de ítem creado: '{datos['nombre']}'")
                return True, ""
        except sqlite3.IntegrityError:
            return False, f"Ya existe un tipo llamado '{datos['nombre']}'."
        except Exception as e:
            log.error(f"TiposController.agregar: {e}")
            return False, str(e)

    def editar(self, tipo_id: int, datos: dict) -> tuple[bool, str]:
        """
        Cambia nombre, comportamiento, descripción o si está activo.
        El comportamiento no se puede cambiar si hay préstamos activos de ese tipo.
        """
        ok, msg = self._validar(datos)
        if not ok:
            return False, msg
        actual = self.obtener_por_id(tipo_id)
        if actual is None:
            return False, "Tipo no encontrado."

        if datos["comportamiento"] != actual["comportamiento"]:
            if self._prestados(tipo_id) > 0:
                return False, ("No se puede cambiar el comportamiento: hay ítems de este "
                               "tipo prestados. Registra primero sus devoluciones.")
        try:
            with conexion() as conn:
                conn.execute("""
                    UPDATE tipos_item
                    SET nombre = ?, comportamiento = ?, descripcion = ?, activo = ?
                    WHERE id = ?
                """, (
                    str(datos["nombre"]).strip(),
                    datos["comportamiento"],
                    str(datos.get("descripcion", "") or "").strip() or None,
                    1 if datos.get("activo", actual["activo"]) else 0,
                    tipo_id,
                ))
                conn.commit()
                log.info(f"Tipo de ítem {tipo_id} actualizado.")
                return True, ""
        except sqlite3.IntegrityError:
            return False, f"Ya existe un tipo llamado '{datos['nombre']}'."
        except Exception as e:
            log.error(f"TiposController.editar: {e}")
            return False, str(e)

    def eliminar(self, tipo_id: int) -> tuple[bool, str]:
        """Borra un tipo solo si ningún ítem lo usa. Si lo usan, conviene desactivarlo."""
        tipo = self.obtener_por_id(tipo_id)
        if tipo is None:
            return False, "Tipo no encontrado."
        if tipo["total_items"] > 0:
            return False, (f"Hay {tipo['total_items']} ítems de tipo '{tipo['nombre']}'. "
                           "Desactívalo en lugar de eliminarlo.")
        try:
            with conexion() as conn:
                conn.execute("DELETE FROM tipos_item WHERE id = ?", (tipo_id,))
                conn.commit()
                log.info(f"Tipo de ítem {tipo_id} eliminado.")
                return True, ""
        except Exception as e:
            log.error(f"TiposController.eliminar: {e}")
            return False, str(e)

    # ── Internos ───────────────────────────────────────────────────────────

    def _validar(self, datos: dict) -> tuple[bool, str]:
        ok, msg = validators.campo_requerido(datos.get("nombre"), "Nombre")
        if not ok:
            return False, msg
        if datos.get("comportamiento") not in COMPORTAMIENTOS_VALIDOS:
            return False, "El comportamiento debe ser 'presta' o 'consume'."
        return True, ""

    def _prestados(self, tipo_id: int) -> int:
        """Cuántas unidades de ítems de este tipo están prestadas ahora."""
        with conexion() as conn:
            total = conn.execute(
                "SELECT COALESCE(SUM(cantidad_prest), 0) FROM items WHERE tipo_id = ?", (tipo_id,)
            ).fetchone()[0]
            return total
