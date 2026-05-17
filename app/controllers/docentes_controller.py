"""
app/controllers/docentes_controller.py
---------------------------------------
Gestión de docentes y usuarios del sistema.
Dos clases separadas para mantener cada responsabilidad clara y pequeña.

DocentesController  →  CRUD de la tabla docentes
UsuariosController  →  CRUD de la tabla usuarios (solicitantes de préstamos)
"""

from db.database          import obtener_conexion
from app.utils.logger     import log
from app.utils            import validators


# ─────────────────────────────────────────────────────────────────────────────
#  DOCENTES
# ─────────────────────────────────────────────────────────────────────────────

class DocentesController:
    """
    Maneja la tabla docentes.
    Los docentes son los responsables de préstamos (quien autoriza o para quien
    se hace el préstamo), según el Excel original.
    """

    def obtener_todos(self) -> list[dict]:
        """Retorna todos los docentes activos ordenados por nombre."""
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM docentes WHERE activo = 1 ORDER BY nombre COLLATE NOCASE
            """)
            resultado = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return resultado
        except Exception as e:
            log.error(f"DocentesController.obtener_todos: {e}")
            return []

    def obtener_por_id(self, docente_id: int) -> dict | None:
        """Retorna un docente por su ID."""
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM docentes WHERE id = ?", (docente_id,))
            fila = cursor.fetchone()
            conn.close()
            return dict(fila) if fila else None
        except Exception as e:
            log.error(f"DocentesController.obtener_por_id({docente_id}): {e}")
            return None

    def buscar(self, texto: str) -> list[dict]:
        """Busca docentes por nombre o correo."""
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            patron = f"%{texto.strip()}%"
            cursor.execute("""
                SELECT * FROM docentes
                WHERE  activo = 1
                  AND (nombre LIKE ? OR correo LIKE ?)
                ORDER  BY nombre COLLATE NOCASE
            """, (patron, patron))
            resultado = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return resultado
        except Exception as e:
            log.error(f"DocentesController.buscar('{texto}'): {e}")
            return []

    def agregar(self, datos: dict) -> tuple[bool, str]:
        """
        Agrega un docente nuevo.

        datos esperado:
            nombre  (str, obligatorio)
            correo  (str, obligatorio)
            motivo  (str, opcional — motivo habitual de sus préstamos)

        Retorna (True, "") o (False, "mensaje de error").
        """
        ok, msg = validators.formulario({
            "Nombre": datos.get("nombre"),
            "Correo": datos.get("correo"),
        })
        if not ok:
            return False, msg

        ok, msg = validators.correo(datos.get("correo", ""))
        if not ok:
            return False, msg

        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO docentes (nombre, correo, motivo)
                VALUES (?, ?, ?)
            """, (
                str(datos["nombre"]).strip(),
                str(datos["correo"]).strip().lower(),
                str(datos.get("motivo", "") or "").strip() or None,
            ))
            conn.commit()
            conn.close()
            log.info(f"Docente agregado: {datos['nombre']}")
            return True, ""
        except Exception as e:
            if "UNIQUE" in str(e):
                return False, "Ya existe un docente registrado con ese correo."
            log.error(f"DocentesController.agregar: {e}")
            return False, str(e)

    def editar(self, docente_id: int, datos: dict) -> tuple[bool, str]:
        """Actualiza nombre, correo y motivo de un docente."""
        ok, msg = validators.formulario({
            "Nombre": datos.get("nombre"),
            "Correo": datos.get("correo"),
        })
        if not ok:
            return False, msg

        ok, msg = validators.correo(datos.get("correo", ""))
        if not ok:
            return False, msg

        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE docentes SET
                    nombre = ?,
                    correo = ?,
                    motivo = ?
                WHERE id = ?
            """, (
                str(datos["nombre"]).strip(),
                str(datos["correo"]).strip().lower(),
                str(datos.get("motivo", "") or "").strip() or None,
                docente_id,
            ))
            conn.commit()
            conn.close()
            log.info(f"Docente {docente_id} actualizado.")
            return True, ""
        except Exception as e:
            if "UNIQUE" in str(e):
                return False, "Ese correo ya está registrado en otro docente."
            log.error(f"DocentesController.editar({docente_id}): {e}")
            return False, str(e)

    def desactivar(self, docente_id: int) -> tuple[bool, str]:
        """
        Desactiva un docente en vez de eliminarlo.
        Preserva el historial de préstamos asociados.
        """
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE docentes SET activo = 0 WHERE id = ?",
                (docente_id,)
            )
            conn.commit()
            conn.close()
            log.info(f"Docente {docente_id} desactivado.")
            return True, ""
        except Exception as e:
            log.error(f"DocentesController.desactivar({docente_id}): {e}")
            return False, str(e)


# ─────────────────────────────────────────────────────────────────────────────
#  USUARIOS
# ─────────────────────────────────────────────────────────────────────────────

class UsuariosController:
    """
    Maneja la tabla usuarios.
    Los usuarios son los solicitantes de préstamos (estudiantes / personal).
    """

    def obtener_todos(self) -> list[dict]:
        """Retorna todos los usuarios activos ordenados por nombre."""
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, nombre, codigo, correo, telefono, rol, creado_en
                FROM   usuarios
                WHERE  activo = 1
                ORDER  BY nombre COLLATE NOCASE
            """)
            resultado = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return resultado
        except Exception as e:
            log.error(f"UsuariosController.obtener_todos: {e}")
            return []

    def obtener_por_id(self, usuario_id: int) -> dict | None:
        """Retorna un usuario por su ID."""
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, nombre, codigo, correo, telefono, rol FROM usuarios WHERE id = ?",
                (usuario_id,)
            )
            fila = cursor.fetchone()
            conn.close()
            return dict(fila) if fila else None
        except Exception as e:
            log.error(f"UsuariosController.obtener_por_id({usuario_id}): {e}")
            return None

    def buscar_por_codigo(self, codigo: str) -> dict | None:
        """
        Busca un usuario por su código estudiantil o institucional.
        Retorna el dict del usuario o None si no existe.
        """
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, nombre, codigo, correo, telefono, rol
                FROM   usuarios
                WHERE  codigo = ? AND activo = 1
            """, (str(codigo).strip(),))
            fila = cursor.fetchone()
            conn.close()
            return dict(fila) if fila else None
        except Exception as e:
            log.error(f"UsuariosController.buscar_por_codigo('{codigo}'): {e}")
            return None

    def buscar(self, texto: str) -> list[dict]:
        """Busca usuarios por nombre o código."""
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            patron = f"%{texto.strip()}%"
            cursor.execute("""
                SELECT id, nombre, codigo, correo, telefono, rol
                FROM   usuarios
                WHERE  activo = 1
                  AND (nombre LIKE ? OR codigo LIKE ?)
                ORDER  BY nombre COLLATE NOCASE
            """, (patron, patron))
            resultado = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return resultado
        except Exception as e:
            log.error(f"UsuariosController.buscar('{texto}'): {e}")
            return []

    def agregar(self, datos: dict) -> tuple[bool, str]:
        """
        Agrega un usuario nuevo (solicitante de préstamos).

        datos esperado:
            nombre    (str, obligatorio)
            codigo    (str, obligatorio — código estudiantil)
            correo    (str, opcional)
            telefono  (str, opcional)
            rol       (str, por defecto 'usuario')

        Retorna (True, "") o (False, "mensaje de error").
        """
        ok, msg = validators.formulario({
            "Nombre": datos.get("nombre"),
            "Código": datos.get("codigo"),
        })
        if not ok:
            return False, msg

        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usuarios (nombre, codigo, correo, telefono, rol)
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(datos["nombre"]).strip(),
                str(datos["codigo"]).strip(),
                str(datos.get("correo", "") or "").strip() or None,
                str(datos.get("telefono", "") or "").strip() or None,
                str(datos.get("rol", "usuario")),
            ))
            conn.commit()
            conn.close()
            log.info(f"Usuario agregado: {datos['nombre']} ({datos['codigo']})")
            return True, ""
        except Exception as e:
            if "UNIQUE" in str(e):
                return False, "Ya existe un usuario con ese código."
            log.error(f"UsuariosController.agregar: {e}")
            return False, str(e)

    def editar(self, usuario_id: int, datos: dict) -> tuple[bool, str]:
        """Actualiza nombre, correo y teléfono de un usuario."""
        ok, msg = validators.formulario({"Nombre": datos.get("nombre")})
        if not ok:
            return False, msg

        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE usuarios SET
                    nombre   = ?,
                    correo   = ?,
                    telefono = ?
                WHERE id = ?
            """, (
                str(datos["nombre"]).strip(),
                str(datos.get("correo", "") or "").strip() or None,
                str(datos.get("telefono", "") or "").strip() or None,
                usuario_id,
            ))
            conn.commit()
            conn.close()
            log.info(f"Usuario {usuario_id} actualizado.")
            return True, ""
        except Exception as e:
            log.error(f"UsuariosController.editar({usuario_id}): {e}")
            return False, str(e)

    def desactivar(self, usuario_id: int) -> tuple[bool, str]:
        """Desactiva un usuario preservando su historial de préstamos."""
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE usuarios SET activo = 0 WHERE id = ?",
                (usuario_id,)
            )
            conn.commit()
            conn.close()
            log.info(f"Usuario {usuario_id} desactivado.")
            return True, ""
        except Exception as e:
            log.error(f"UsuariosController.desactivar({usuario_id}): {e}")
            return False, str(e)
