"""
app/controllers/inventario_controller.py
-----------------------------------------
Lógica de negocio para inventario y depósitos.

Clases:
    DepositosController  — CRUD de depósitos (solo admin puede crear/editar/eliminar)
    InventarioController — CRUD de ítems

Todo acceso a la base usa `with conexion() as conn:` (db/database.py), que cierra
la conexión siempre, incluso si hay un error. Así nunca queda la base bloqueada.
"""

import sqlite3

from db.database          import conexion
from app.utils.logger     import log
from app.utils            import validators
from app.controllers.tipos_controller import TiposController
from config.constants     import PRESTAMO_ACTIVO


# ─────────────────────────────────────────────────────────────────────────────
#  DEPÓSITOS
# ─────────────────────────────────────────────────────────────────────────────

class DepositosController:
    """
    CRUD de depósitos/espacios de almacenamiento.
    El admin puede crear depósitos con cualquier nombre:
    'Depósito 1', 'Laboratorio A', 'Salón 201', 'Vitrina', etc.
    """

    def obtener_todos(self) -> list[dict]:
        """Retorna todos los depósitos con su conteo de ítems."""
        try:
            with conexion() as conn:
                filas = conn.execute("""
                    SELECT d.id, d.nombre, d.descripcion,
                           COUNT(i.id) AS total_items
                    FROM   depositos d
                    LEFT JOIN items i ON i.deposito_id = d.id
                    GROUP  BY d.id
                    ORDER  BY d.nombre COLLATE NOCASE
                """).fetchall()
            return [dict(r) for r in filas]
        except Exception as e:
            log.error(f"DepositosController.obtener_todos: {e}")
            return []

    def obtener_por_id(self, deposito_id: int) -> dict | None:
        try:
            with conexion() as conn:
                fila = conn.execute("SELECT * FROM depositos WHERE id = ?", (deposito_id,)).fetchone()
            return dict(fila) if fila else None
        except Exception as e:
            log.error(f"DepositosController.obtener_por_id: {e}")
            return None

    def agregar(self, datos: dict) -> tuple[bool, str]:
        """
        Crea un depósito nuevo.
        datos: nombre (obligatorio), descripcion (opcional)
        """
        ok, msg = validators.formulario({"Nombre": datos.get("nombre")})
        if not ok:
            return False, msg

        ok, msg = validators.longitud(datos.get("nombre", ""), "Nombre", 2, 100)
        if not ok:
            return False, msg

        try:
            with conexion() as conn:
                conn.execute("""
                    INSERT INTO depositos (nombre, descripcion) VALUES (?, ?)
                """, (
                    str(datos["nombre"]).strip(),
                    str(datos.get("descripcion", "") or "").strip() or None,
                ))
                conn.commit()
            log.info(f"Depósito creado: '{datos['nombre']}'")
            return True, ""
        except Exception as e:
            if "UNIQUE" in str(e):
                return False, f"Ya existe un depósito llamado '{datos['nombre']}'."
            log.error(f"DepositosController.agregar: {e}")
            return False, str(e)

    def editar(self, deposito_id: int, datos: dict) -> tuple[bool, str]:
        """Actualiza nombre y descripción."""
        ok, msg = validators.formulario({"Nombre": datos.get("nombre")})
        if not ok:
            return False, msg

        try:
            with conexion() as conn:
                conn.execute("""
                    UPDATE depositos SET nombre = ?, descripcion = ? WHERE id = ?
                """, (
                    str(datos["nombre"]).strip(),
                    str(datos.get("descripcion", "") or "").strip() or None,
                    deposito_id,
                ))
                conn.commit()
            log.info(f"Depósito {deposito_id} actualizado.")
            return True, ""
        except Exception as e:
            if "UNIQUE" in str(e):
                return False, "Ya existe un depósito con ese nombre."
            log.error(f"DepositosController.editar: {e}")
            return False, str(e)

    def eliminar(self, deposito_id: int) -> tuple[bool, str]:
        """
        Elimina solo si no tiene ítems asociados.
        Protege la integridad del inventario.
        """
        try:
            with conexion() as conn:
                total = conn.execute(
                    "SELECT COUNT(*) AS total FROM items WHERE deposito_id = ?", (deposito_id,)
                ).fetchone()["total"]
                if total > 0:
                    return False, (
                        f"No se puede eliminar: el depósito tiene {total} ítem(s).\n"
                        "Primero elimina o mueve los ítems."
                    )
                conn.execute("DELETE FROM depositos WHERE id = ?", (deposito_id,))
                conn.commit()
            log.info(f"Depósito {deposito_id} eliminado.")
            return True, ""
        except Exception as e:
            log.error(f"DepositosController.eliminar: {e}")
            return False, str(e)


# ─────────────────────────────────────────────────────────────────────────────
#  ÍTEMS
# ─────────────────────────────────────────────────────────────────────────────

class InventarioController:

    def obtener_depositos(self) -> list[dict]:
        return DepositosController().obtener_todos()

    def obtener_items_por_deposito(self, deposito_id: int) -> list[dict]:
        try:
            with conexion() as conn:
                filas = conn.execute("""
                    SELECT i.id, i.nombre, i.referencia,
                           i.cantidad_total, i.cantidad_disp, i.cantidad_prest,
                           i.veces_prestado, i.ubicacion, i.observaciones,
                           d.nombre AS deposito
                    FROM   items i
                    JOIN   depositos d ON d.id = i.deposito_id
                    WHERE  i.deposito_id = ?
                    ORDER  BY i.nombre COLLATE NOCASE
                """, (deposito_id,)).fetchall()
            return [dict(r) for r in filas]
        except Exception as e:
            log.error(f"InventarioController.obtener_items_por_deposito: {e}")
            return []

    def obtener_todos_los_items(self) -> list[dict]:
        try:
            with conexion() as conn:
                filas = conn.execute("""
                    SELECT i.*, d.nombre AS deposito
                    FROM   items i
                    JOIN   depositos d ON d.id = i.deposito_id
                    ORDER  BY d.nombre, i.nombre COLLATE NOCASE
                """).fetchall()
            return [dict(r) for r in filas]
        except Exception as e:
            log.error(f"InventarioController.obtener_todos_los_items: {e}")
            return []

    def obtener_item_por_id(self, item_id: int) -> dict | None:
        try:
            with conexion() as conn:
                fila = conn.execute("""
                    SELECT i.*, d.nombre AS deposito
                    FROM   items i
                    JOIN   depositos d ON d.id = i.deposito_id
                    WHERE  i.id = ?
                """, (item_id,)).fetchone()
            return dict(fila) if fila else None
        except Exception as e:
            log.error(f"InventarioController.obtener_item_por_id: {e}")
            return None

    def buscar_items(self, texto: str) -> list[dict]:
        try:
            patron = f"%{texto.strip()}%"
            with conexion() as conn:
                filas = conn.execute("""
                    SELECT i.*, d.nombre AS deposito
                    FROM   items i
                    JOIN   depositos d ON d.id = i.deposito_id
                    WHERE  i.nombre LIKE ? OR i.referencia LIKE ?
                    ORDER  BY i.nombre COLLATE NOCASE
                """, (patron, patron)).fetchall()
            return [dict(r) for r in filas]
        except Exception as e:
            log.error(f"InventarioController.buscar_items: {e}")
            return []

    def agregar_item(self, datos: dict) -> tuple[bool, str]:
        ok, msg = validators.formulario({
            "Nombre":   datos.get("nombre"),
            "Depósito": datos.get("deposito_id"),
        })
        if not ok:
            return False, msg

        ok, msg = validators.numero_positivo(datos.get("cantidad_total", 0), "Cantidad")
        if not ok:
            return False, msg

        # Tipo del ítem: el indicado (tipo_id) o, si no se indica, el tipo por defecto
        tipo_id = datos.get("tipo_id")
        if not tipo_id:
            por_defecto = TiposController().tipo_por_defecto()
            tipo_id = por_defecto["id"] if por_defecto else None

        try:
            cantidad = int(datos.get("cantidad_total", 0))
            with conexion() as conn:
                conn.execute("""
                    INSERT INTO items
                        (deposito_id, nombre, referencia, cantidad_total,
                         cantidad_disp, ubicacion, observaciones, tipo_id, unidad)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(datos["deposito_id"]),
                    str(datos["nombre"]).strip(),
                    str(datos.get("referencia", "") or "").strip() or None,
                    cantidad, cantidad,
                    str(datos.get("ubicacion", "") or "").strip() or None,
                    str(datos.get("observaciones", "") or "").strip() or None,
                    tipo_id,
                    str(datos.get("unidad", "") or "").strip() or None,
                ))
                conn.commit()
            log.info(f"Ítem agregado: '{datos['nombre']}'")
            return True, ""
        except Exception as e:
            log.error(f"InventarioController.agregar_item: {e}")
            return False, str(e)

    def editar_item(self, item_id: int, datos: dict) -> tuple[bool, str]:
        ok, msg = validators.formulario({"Nombre": datos.get("nombre")})
        if not ok:
            return False, msg

        ok, msg = validators.numero_positivo(datos.get("cantidad_total", 0), "Cantidad total")
        if not ok:
            return False, msg

        try:
            with conexion() as conn:
                actual = conn.execute(
                    "SELECT cantidad_prest FROM items WHERE id = ?", (item_id,)
                ).fetchone()
                if not actual:
                    return False, "Ítem no encontrado."

                nueva_cantidad = int(datos.get("cantidad_total", 0))
                nueva_disp     = max(0, nueva_cantidad - actual["cantidad_prest"])

                conn.execute("""
                    UPDATE items SET
                        nombre = ?, referencia = ?,
                        cantidad_total = ?, cantidad_disp = ?,
                        ubicacion = ?, observaciones = ?
                    WHERE id = ?
                """, (
                    str(datos["nombre"]).strip(),
                    str(datos.get("referencia", "") or "").strip() or None,
                    nueva_cantidad, nueva_disp,
                    str(datos.get("ubicacion", "") or "").strip() or None,
                    str(datos.get("observaciones", "") or "").strip() or None,
                    item_id,
                ))
                conn.commit()
            log.info(f"Ítem {item_id} actualizado.")
            return True, ""
        except Exception as e:
            log.error(f"InventarioController.editar_item: {e}")
            return False, str(e)

    def contar_historial(self, item_id: int) -> int:
        """Cuántos movimientos del historial tiene el ítem (para avisar antes de eliminarlo)."""
        try:
            with conexion() as conn:
                return conn.execute("SELECT COUNT(*) FROM movimientos WHERE item_id = ?",
                                    (item_id,)).fetchone()[0]
        except Exception as e:
            log.error(f"InventarioController.contar_historial: {e}")
            return 0

    def eliminar_item(self, item_id: int) -> tuple[bool, str]:
        """
        Elimina un ítem. Solo se impide si tiene préstamos ACTIVOS (hay que devolverlos primero).
        Si tiene historial, el historial se conserva: la base guarda el nombre del ítem en cada
        movimiento y el historial lo muestra marcado como eliminado (ver migration_004.py).
        """
        try:
            with conexion() as conn:
                item = conn.execute("SELECT nombre FROM items WHERE id = ?", (item_id,)).fetchone()
                if not item:
                    return False, "Ítem no encontrado."

                activos = conn.execute(
                    "SELECT COUNT(*) FROM prestamos WHERE item_id = ? AND estado = ?",
                    (item_id, PRESTAMO_ACTIVO)).fetchone()[0]
                if activos:
                    return False, "No se puede eliminar: el ítem tiene préstamos activos."

                conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
                conn.commit()
            log.info(f"Ítem {item_id} eliminado.")
            return True, ""
        except sqlite3.IntegrityError:
            return False, "No se puede eliminar: hay otros registros que dependen de este ítem."
        except Exception as e:
            log.error(f"InventarioController.eliminar_item: {e}")
            return False, str(e)
