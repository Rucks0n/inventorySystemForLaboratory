"""
app/controllers/auth_controller.py
------------------------------------
Autenticación de usuarios que acceden al sistema (no de solicitantes de préstamos).
La UI de login llama a este controller — nunca toca la BD directamente.

Uso:
    auth = AuthController()
    usuario = auth.login("admin", "admin123")
    if usuario:
        # usuario es un dict: {"id": 1, "nombre": "Admin", "rol": "admin", ...}
"""

import hashlib
from db.database          import obtener_conexion
from app.utils.logger     import log
from config.constants     import ROL_ADMIN


def _hash(contrasena: str) -> str:
    """Convierte la contraseña en SHA-256. Nunca se guarda en texto plano."""
    return hashlib.sha256(contrasena.encode("utf-8")).hexdigest()


class AuthController:

    def login(self, codigo: str, contrasena: str) -> dict | None:
        """
        Verifica las credenciales de acceso al sistema.

        Parámetros:
            codigo:     código o nombre de usuario
            contrasena: contraseña en texto plano (se hashea internamente)

        Retorna:
            dict con datos del usuario si las credenciales son válidas y el usuario está activo.
            None si son incorrectas o el usuario está inactivo.
        """
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, nombre, codigo, correo, rol
                FROM   usuarios
                WHERE  codigo     = ?
                  AND  contrasena = ?
                  AND  activo     = 1
            """, (str(codigo).strip(), _hash(contrasena)))
            fila = cursor.fetchone()
            conn.close()

            if fila:
                log.info(f"Login exitoso: {codigo} (rol={fila['rol']})")
                return dict(fila)

            log.warning(f"Login fallido: {codigo}")
            return None

        except Exception as e:
            log.error(f"AuthController.login: {e}")
            return None

    def crear_usuario_sistema(
        self,
        nombre: str,
        codigo: str,
        contrasena: str,
        rol: str = ROL_ADMIN
    ) -> tuple[bool, str]:
        """
        Crea un usuario con acceso al sistema (con contraseña).
        Se usa en la primera ejecución para crear el admin por defecto,
        y también desde la UI de administración de usuarios.

        Retorna (True, "") o (False, "mensaje de error").
        """
        if not nombre or not codigo or not contrasena:
            return False, "Nombre, código y contraseña son obligatorios."

        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO usuarios
                    (nombre, codigo, contrasena, rol, activo)
                VALUES (?, ?, ?, ?, 1)
            """, (
                str(nombre).strip(),
                str(codigo).strip(),
                _hash(contrasena),
                str(rol),
            ))
            conn.commit()
            conn.close()
            log.info(f"Usuario de sistema creado: {codigo} (rol={rol})")
            return True, ""
        except Exception as e:
            if "UNIQUE" in str(e):
                return False, f"El código '{codigo}' ya está registrado."
            log.error(f"AuthController.crear_usuario_sistema: {e}")
            return False, str(e)

    def cambiar_contrasena(
        self,
        usuario_id: int,
        contrasena_actual: str,
        nueva_contrasena: str
    ) -> tuple[bool, str]:
        """
        Cambia la contraseña de un usuario verificando la contraseña actual.

        Retorna (True, "") o (False, "mensaje de error").
        """
        if not nueva_contrasena or len(nueva_contrasena) < 6:
            return False, "La nueva contraseña debe tener al menos 6 caracteres."

        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()

            # Verificar contraseña actual
            cursor.execute("""
                SELECT id FROM usuarios
                WHERE  id = ? AND contrasena = ?
            """, (usuario_id, _hash(contrasena_actual)))

            if not cursor.fetchone():
                conn.close()
                return False, "La contraseña actual no es correcta."

            cursor.execute("""
                UPDATE usuarios SET contrasena = ? WHERE id = ?
            """, (_hash(nueva_contrasena), usuario_id))

            conn.commit()
            conn.close()
            log.info(f"Contraseña actualizada para usuario {usuario_id}.")
            return True, ""

        except Exception as e:
            log.error(f"AuthController.cambiar_contrasena: {e}")
            return False, str(e)
