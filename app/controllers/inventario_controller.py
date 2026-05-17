"""
app/controllers/inventario_controller.py
-----------------------------------------
Lógica de negocio para inventario.
La UI llama a este controller — nunca toca la BD directamente.

Métodos principales:
    obtener_depositos()
    obtener_items_por_deposito(deposito_id)
    obtener_todos_los_items()
    buscar_items(texto)
    agregar_item(datos)
    editar_item(item_id, datos)
    eliminar_item(item_id)
"""

from db.database          import obtener_conexion
from app.utils.logger     import log
from app.utils            import validators


class InventarioController:

    # ── Depósitos ──────────────────────────────────────────────────────────────

    def obtener_depositos(self) -> list[dict]:
        """Retorna todos los depósitos registrados."""
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM depositos ORDER BY nombre")
            resultado = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return resultado
        except Exception as e:
            log.error(f"obtener_depositos: {e}")
            return []

    # ── Ítems ──────────────────────────────────────────────────────────────────

    def obtener_items_por_deposito(self, deposito_id: int) -> list[dict]:
        """
        Retorna todos los ítems de un depósito específico.
        Incluye el nombre del depósito para mostrarlo en la tabla.
        """
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    i.id,
                    i.nombre,
                    i.referencia,
                    i.cantidad_total,
                    i.cantidad_disp,
                    i.cantidad_prest,
                    i.veces_prestado,
                    i.ubicacion,
                    i.observaciones,
                    d.nombre AS deposito
                FROM   items i
                JOIN   depositos d ON d.id = i.deposito_id
                WHERE  i.deposito_id = ?
                ORDER  BY i.nombre COLLATE NOCASE
            """, (deposito_id,))
            resultado = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return resultado
        except Exception as e:
            log.error(f"obtener_items_por_deposito({deposito_id}): {e}")
            return []

    def obtener_todos_los_items(self) -> list[dict]:
        """Retorna todos los ítems de todos los depósitos."""
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    i.id, i.nombre, i.referencia,
                    i.cantidad_total, i.cantidad_disp, i.cantidad_prest,
                    i.veces_prestado, i.ubicacion, i.observaciones,
                    d.nombre AS deposito
                FROM   items i
                JOIN   depositos d ON d.id = i.deposito_id
                ORDER  BY d.nombre, i.nombre COLLATE NOCASE
            """)
            resultado = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return resultado
        except Exception as e:
            log.error(f"obtener_todos_los_items: {e}")
            return []

    def obtener_item_por_id(self, item_id: int) -> dict | None:
        """Retorna un ítem por su ID, o None si no existe."""
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.*, d.nombre AS deposito
                FROM   items i
                JOIN   depositos d ON d.id = i.deposito_id
                WHERE  i.id = ?
            """, (item_id,))
            fila = cursor.fetchone()
            conn.close()
            return dict(fila) if fila else None
        except Exception as e:
            log.error(f"obtener_item_por_id({item_id}): {e}")
            return None

    def buscar_items(self, texto: str) -> list[dict]:
        """
        Búsqueda por nombre o referencia en todos los depósitos.
        No sensible a mayúsculas.
        """
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            patron = f"%{texto.strip()}%"
            cursor.execute("""
                SELECT i.*, d.nombre AS deposito
                FROM   items i
                JOIN   depositos d ON d.id = i.deposito_id
                WHERE  i.nombre     LIKE ? OR
                       i.referencia LIKE ?
                ORDER  BY i.nombre COLLATE NOCASE
            """, (patron, patron))
            resultado = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return resultado
        except Exception as e:
            log.error(f"buscar_items('{texto}'): {e}")
            return []

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def agregar_item(self, datos: dict) -> tuple[bool, str]:
        """
        Agrega un ítem nuevo al inventario.

        datos esperado:
            deposito_id   (int, obligatorio)
            nombre        (str, obligatorio)
            referencia    (str, opcional)
            cantidad_total(int, >= 0)
            ubicacion     (str, opcional)
            observaciones (str, opcional)

        Retorna (True, "") o (False, "mensaje de error").
        """
        ok, msg = validators.formulario({
            "Nombre":   datos.get("nombre"),
            "Depósito": datos.get("deposito_id"),
        })
        if not ok:
            return False, msg

        ok, msg = validators.numero_positivo(datos.get("cantidad_total", 0), "Cantidad")
        if not ok:
            return False, msg

        try:
            cantidad = int(datos.get("cantidad_total", 0))
            conn     = obtener_conexion()
            cursor   = conn.cursor()
            cursor.execute("""
                INSERT INTO items
                    (deposito_id, nombre, referencia, cantidad_total,
                     cantidad_disp, ubicacion, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                int(datos["deposito_id"]),
                str(datos["nombre"]).strip(),
                str(datos.get("referencia", "") or "").strip() or None,
                cantidad,
                cantidad,
                str(datos.get("ubicacion", "") or "").strip() or None,
                str(datos.get("observaciones", "") or "").strip() or None,
            ))
            conn.commit()
            conn.close()
            log.info(f"Ítem agregado: '{datos['nombre']}'")
            return True, ""
        except Exception as e:
            log.error(f"agregar_item: {e}")
            return False, str(e)

    def editar_item(self, item_id: int, datos: dict) -> tuple[bool, str]:
        """
        Actualiza nombre, referencia, cantidad total, ubicación y observaciones.
        No modifica cantidad_disp ni cantidad_prest directamente.
        """
        ok, msg = validators.formulario({"Nombre": datos.get("nombre")})
        if not ok:
            return False, msg

        ok, msg = validators.numero_positivo(datos.get("cantidad_total", 0), "Cantidad total")
        if not ok:
            return False, msg

        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()

            # Obtener el ítem actual para recalcular disponibilidad
            cursor.execute(
                "SELECT cantidad_total, cantidad_prest FROM items WHERE id = ?",
                (item_id,)
            )
            actual = cursor.fetchone()
            if not actual:
                conn.close()
                return False, "Ítem no encontrado."

            nueva_cantidad = int(datos.get("cantidad_total", 0))
            nueva_disp     = max(0, nueva_cantidad - actual["cantidad_prest"])

            cursor.execute("""
                UPDATE items SET
                    nombre         = ?,
                    referencia     = ?,
                    cantidad_total = ?,
                    cantidad_disp  = ?,
                    ubicacion      = ?,
                    observaciones  = ?
                WHERE id = ?
            """, (
                str(datos["nombre"]).strip(),
                str(datos.get("referencia", "") or "").strip() or None,
                nueva_cantidad,
                nueva_disp,
                str(datos.get("ubicacion", "") or "").strip() or None,
                str(datos.get("observaciones", "") or "").strip() or None,
                item_id,
            ))
            conn.commit()
            conn.close()
            log.info(f"Ítem {item_id} actualizado.")
            return True, ""
        except Exception as e:
            log.error(f"editar_item({item_id}): {e}")
            return False, str(e)

    def eliminar_item(self, item_id: int) -> tuple[bool, str]:
        """
        Elimina un ítem del inventario.
        Falla si el ítem tiene préstamos activos (para no perder historial).
        """
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) AS total FROM prestamos
                WHERE  item_id = ? AND estado = 'activo'
            """, (item_id,))
            activos = cursor.fetchone()["total"]

            if activos > 0:
                conn.close()
                return False, f"No se puede eliminar: el ítem tiene {activos} préstamo(s) activo(s)."

            cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()
            log.info(f"Ítem {item_id} eliminado.")
            return True, ""
        except Exception as e:
            log.error(f"eliminar_item({item_id}): {e}")
            return False, str(e)
