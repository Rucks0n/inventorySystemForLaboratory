"""
app/controllers/inventario_controller.py
-----------------------------------------
Lógica de negocio para inventario y depósitos.

Clases:
    DepositosController  — CRUD de depósitos (solo admin puede crear/editar/eliminar)
    InventarioController — CRUD de ítems
"""

from db.database          import obtener_conexion
from app.utils.logger     import log
from app.utils            import validators


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
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d.id, d.nombre, d.descripcion,
                       COUNT(i.id) AS total_items
                FROM   depositos d
                LEFT JOIN items i ON i.deposito_id = d.id
                GROUP  BY d.id
                ORDER  BY d.nombre COLLATE NOCASE
            """)
            resultado = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return resultado
        except Exception as e:
            log.error(f"DepositosController.obtener_todos: {e}")
            return []

    def obtener_por_id(self, deposito_id: int) -> dict | None:
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM depositos WHERE id = ?", (deposito_id,))
            fila = cursor.fetchone()
            conn.close()
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
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO depositos (nombre, descripcion) VALUES (?, ?)
            """, (
                str(datos["nombre"]).strip(),
                str(datos.get("descripcion", "") or "").strip() or None,
            ))
            conn.commit()
            conn.close()
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
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE depositos SET nombre = ?, descripcion = ? WHERE id = ?
            """, (
                str(datos["nombre"]).strip(),
                str(datos.get("descripcion", "") or "").strip() or None,
                deposito_id,
            ))
            conn.commit()
            conn.close()
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
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) AS total FROM items WHERE deposito_id = ?",
                (deposito_id,)
            )
            total = cursor.fetchone()["total"]
            if total > 0:
                conn.close()
                return False, (
                    f"No se puede eliminar: el depósito tiene {total} ítem(s).\n"
                    "Primero elimina o mueve los ítems."
                )
            cursor.execute("DELETE FROM depositos WHERE id = ?", (deposito_id,))
            conn.commit()
            conn.close()
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
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.id, i.nombre, i.referencia,
                       i.cantidad_total, i.cantidad_disp, i.cantidad_prest,
                       i.veces_prestado, i.ubicacion, i.observaciones,
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
            log.error(f"InventarioController.obtener_items_por_deposito: {e}")
            return []

    def obtener_todos_los_items(self) -> list[dict]:
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.*, d.nombre AS deposito
                FROM   items i
                JOIN   depositos d ON d.id = i.deposito_id
                ORDER  BY d.nombre, i.nombre COLLATE NOCASE
            """)
            resultado = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return resultado
        except Exception as e:
            log.error(f"InventarioController.obtener_todos_los_items: {e}")
            return []

    def obtener_item_por_id(self, item_id: int) -> dict | None:
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
            log.error(f"InventarioController.obtener_item_por_id: {e}")
            return None

    def buscar_items(self, texto: str) -> list[dict]:
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            patron = f"%{texto.strip()}%"
            cursor.execute("""
                SELECT i.*, d.nombre AS deposito
                FROM   items i
                JOIN   depositos d ON d.id = i.deposito_id
                WHERE  i.nombre LIKE ? OR i.referencia LIKE ?
                ORDER  BY i.nombre COLLATE NOCASE
            """, (patron, patron))
            resultado = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return resultado
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
                cantidad, cantidad,
                str(datos.get("ubicacion", "") or "").strip() or None,
                str(datos.get("observaciones", "") or "").strip() or None,
            ))
            conn.commit()
            conn.close()
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
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT cantidad_prest FROM items WHERE id = ?", (item_id,)
            )
            actual = cursor.fetchone()
            if not actual:
                conn.close()
                return False, "Ítem no encontrado."

            nueva_cantidad = int(datos.get("cantidad_total", 0))
            nueva_disp     = max(0, nueva_cantidad - actual["cantidad_prest"])

            cursor.execute("""
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
            conn.close()
            log.info(f"Ítem {item_id} actualizado.")
            return True, ""
        except Exception as e:
            log.error(f"InventarioController.editar_item: {e}")
            return False, str(e)

    def eliminar_item(self, item_id: int) -> tuple[bool, str]:
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) AS total FROM prestamos
                WHERE  item_id = ? AND estado = 'activo'
            """, (item_id,))
            if cursor.fetchone()["total"] > 0:
                conn.close()
                return False, "No se puede eliminar: el ítem tiene préstamos activos."
            cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()
            log.info(f"Ítem {item_id} eliminado.")
            return True, ""
        except Exception as e:
            log.error(f"InventarioController.eliminar_item: {e}")
            return False, str(e)
