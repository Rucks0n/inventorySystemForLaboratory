"""
app/controllers/prestamos_controller.py
-----------------------------------------
Lógica de préstamos y devoluciones.
Actualiza automáticamente el stock del ítem en cada operación.

Flujo completo:
    registrar_prestamo()   →  baja cantidad_disp, sube cantidad_prest
                              registra en movimientos (tipo='Salida')
    registrar_devolucion() →  sube cantidad_disp, baja cantidad_prest
                              registra en devoluciones y movimientos (tipo='Devolución')
"""

from db.database          import obtener_conexion
from app.utils.logger     import log
from app.utils            import validators
from config.constants     import PRESTAMO_ACTIVO, PRESTAMO_DEVUELTO, MOV_SALIDA, MOV_DEVOLUCION


class PrestamosController:

    # ── Consultas ──────────────────────────────────────────────────────────────

    def obtener_activos(self) -> list[dict]:
        """Retorna todos los préstamos con estado 'activo', con detalle completo."""
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    p.id,
                    p.cantidad,
                    p.motivo,
                    p.fecha_prestamo,
                    p.fecha_limite,
                    p.estado,
                    p.observaciones,
                    i.nombre        AS item_nombre,
                    i.referencia    AS item_ref,
                    u.nombre        AS usuario_nombre,
                    u.codigo        AS usuario_codigo,
                    u.correo        AS usuario_correo,
                    u.telefono      AS usuario_telefono,
                    d.nombre        AS docente_nombre
                FROM   prestamos p
                JOIN   items     i ON i.id = p.item_id
                JOIN   usuarios  u ON u.id = p.usuario_id
                LEFT JOIN docentes d ON d.id = p.docente_id
                WHERE  p.estado = ?
                ORDER  BY p.fecha_prestamo DESC
            """, (PRESTAMO_ACTIVO,))
            resultado = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return resultado
        except Exception as e:
            log.error(f"obtener_activos: {e}")
            return []

    def obtener_historial(self, limite: int = 200) -> list[dict]:
        """Retorna el historial de movimientos más recientes."""
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    m.id,
                    m.tipo,
                    m.cantidad,
                    m.motivo,
                    m.fecha,
                    m.observaciones,
                    i.nombre        AS item_nombre,
                    i.referencia    AS item_ref,
                    u.nombre        AS usuario_nombre,
                    u.codigo        AS usuario_codigo,
                    d.nombre        AS docente_nombre
                FROM   movimientos m
                LEFT JOIN items    i ON i.id = m.item_id
                LEFT JOIN usuarios u ON u.id = m.usuario_id
                LEFT JOIN docentes d ON d.id = m.docente_id
                ORDER  BY m.fecha DESC
                LIMIT  ?
            """, (limite,))
            resultado = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return resultado
        except Exception as e:
            log.error(f"obtener_historial: {e}")
            return []

    def obtener_por_id(self, prestamo_id: int) -> dict | None:
        """Retorna un préstamo específico con todos sus datos."""
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, i.nombre AS item_nombre, u.nombre AS usuario_nombre
                FROM   prestamos p
                JOIN   items    i ON i.id = p.item_id
                JOIN   usuarios u ON u.id = p.usuario_id
                WHERE  p.id = ?
            """, (prestamo_id,))
            fila = cursor.fetchone()
            conn.close()
            return dict(fila) if fila else None
        except Exception as e:
            log.error(f"obtener_por_id({prestamo_id}): {e}")
            return None

    # ── Registrar préstamo ─────────────────────────────────────────────────────

    def registrar_prestamo(self, datos: dict) -> tuple[bool, str]:
        """
        Registra un nuevo préstamo y actualiza el stock del ítem.

        datos esperado:
            item_id      (int, obligatorio)
            usuario_id   (int, obligatorio)
            cantidad     (int, obligatorio, >= 1)
            motivo       (str, opcional)
            fecha_limite (str, opcional, formato 'YYYY-MM-DD')
            docente_id   (int, opcional)
            observaciones(str, opcional)

        Retorna (True, "") o (False, "mensaje de error").
        """
        ok, msg = validators.formulario({
            "Ítem":     datos.get("item_id"),
            "Usuario":  datos.get("usuario_id"),
            "Cantidad": datos.get("cantidad"),
        })
        if not ok:
            return False, msg

        ok, msg = validators.numero_entero_positivo(datos.get("cantidad"), "Cantidad")
        if not ok:
            return False, msg

        cantidad = int(datos["cantidad"])

        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()

            # ── Verificar stock disponible ─────────────────────────────────
            cursor.execute(
                "SELECT nombre, cantidad_disp FROM items WHERE id = ?",
                (datos["item_id"],)
            )
            item = cursor.fetchone()

            if not item:
                conn.close()
                return False, "El ítem no existe en el inventario."

            if item["cantidad_disp"] < cantidad:
                conn.close()
                return (
                    False,
                    f"Stock insuficiente. Disponibles: {item['cantidad_disp']}, "
                    f"solicitados: {cantidad}."
                )

            # ── Insertar préstamo ──────────────────────────────────────────
            cursor.execute("""
                INSERT INTO prestamos
                    (item_id, usuario_id, docente_id, cantidad, motivo,
                     fecha_limite, estado, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(datos["item_id"]),
                int(datos["usuario_id"]),
                int(datos["docente_id"]) if datos.get("docente_id") else None,
                cantidad,
                str(datos.get("motivo", "") or "").strip() or None,
                datos.get("fecha_limite") or None,
                PRESTAMO_ACTIVO,
                str(datos.get("observaciones", "") or "").strip() or None,
            ))

            # ── Actualizar stock ───────────────────────────────────────────
            cursor.execute("""
                UPDATE items SET
                    cantidad_disp  = cantidad_disp  - ?,
                    cantidad_prest = cantidad_prest + ?,
                    veces_prestado = veces_prestado + 1
                WHERE id = ?
            """, (cantidad, cantidad, datos["item_id"]))

            # ── Registrar en movimientos ───────────────────────────────────
            cursor.execute("""
                INSERT INTO movimientos
                    (item_id, usuario_id, docente_id, tipo, cantidad, motivo)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                int(datos["item_id"]),
                int(datos["usuario_id"]),
                int(datos["docente_id"]) if datos.get("docente_id") else None,
                MOV_SALIDA,
                cantidad,
                str(datos.get("motivo", "") or "").strip() or None,
            ))

            conn.commit()
            conn.close()
            log.info(
                f"Préstamo registrado: ítem={datos['item_id']} "
                f"usuario={datos['usuario_id']} cantidad={cantidad}"
            )
            return True, ""

        except Exception as e:
            log.error(f"registrar_prestamo: {e}")
            return False, str(e)

    # ── Registrar devolución ───────────────────────────────────────────────────

    def registrar_devolucion(self, prestamo_id: int, observaciones: str = "") -> tuple[bool, str]:
        """
        Registra la devolución completa de un préstamo activo.
        Restaura automáticamente el stock del ítem.

        Retorna (True, "") o (False, "mensaje de error").
        """
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()

            # ── Obtener el préstamo activo ─────────────────────────────────
            cursor.execute("""
                SELECT * FROM prestamos WHERE id = ? AND estado = ?
            """, (prestamo_id, PRESTAMO_ACTIVO))
            prestamo = cursor.fetchone()

            if not prestamo:
                conn.close()
                return False, "El préstamo no existe o ya fue devuelto."

            obs = str(observaciones).strip() or None

            # ── Marcar como devuelto ───────────────────────────────────────
            cursor.execute("""
                UPDATE prestamos SET
                    estado           = ?,
                    fecha_devolucion = datetime('now'),
                    observaciones    = ?
                WHERE id = ?
            """, (PRESTAMO_DEVUELTO, obs, prestamo_id))

            # ── Restaurar stock ────────────────────────────────────────────
            cursor.execute("""
                UPDATE items SET
                    cantidad_disp  = cantidad_disp  + ?,
                    cantidad_prest = MAX(0, cantidad_prest - ?)
                WHERE id = ?
            """, (prestamo["cantidad"], prestamo["cantidad"], prestamo["item_id"]))

            # ── Registrar en devoluciones ──────────────────────────────────
            cursor.execute("""
                INSERT INTO devoluciones
                    (prestamo_id, item_id, usuario_id, cantidad, observaciones)
                VALUES (?, ?, ?, ?, ?)
            """, (
                prestamo_id,
                prestamo["item_id"],
                prestamo["usuario_id"],
                prestamo["cantidad"],
                obs,
            ))

            # ── Registrar en movimientos ───────────────────────────────────
            cursor.execute("""
                INSERT INTO movimientos
                    (item_id, usuario_id, docente_id, tipo, cantidad, observaciones)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                prestamo["item_id"],
                prestamo["usuario_id"],
                prestamo["docente_id"],
                MOV_DEVOLUCION,
                prestamo["cantidad"],
                obs,
            ))

            conn.commit()
            conn.close()
            log.info(f"Devolución registrada: préstamo {prestamo_id}.")
            return True, ""

        except Exception as e:
            log.error(f"registrar_devolucion({prestamo_id}): {e}")
            return False, str(e)
