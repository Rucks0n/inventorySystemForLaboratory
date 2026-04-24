"""
app/controllers/auth_controller.py
------------------------------------
Lógica de autenticación y manejo de sesión.
La UI de login llama a este controller — nunca toca la BD directamente.
"""

import hashlib
from db.database      import obtener_conexion
from app.utils.logger import log


def _hashear(contrasena: str) -> str:
    """Convierte la contraseña a SHA-256 antes de guardar o comparar."""
    return hashlib.sha256(contrasena.encode()).hexdigest()


class AuthController:

    def login(self, usuario: str, contrasena: str) -> dict | None:
        """
        Verifica las credenciales del usuario.

        Retorna:
            Diccionario con datos del usuario si es válido.
            None si el usuario no existe o la contraseña es incorrecta.
        """
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, nombre, usuario, rol
                FROM   usuarios
                WHERE  usuario = ?
                  AND  contrasena = ?
                  AND  activo = 1
            """, (usuario, _hashear(contrasena)))

            fila = cursor.fetchone()
            conn.close()

            if fila:
                return dict(fila)   # {"id": 1, "nombre": "Ana", "rol": "admin"}
            return None

        except Exception as e:
            log.error(f"Error en login: {e}")
            return None

    def crear_usuario_admin(self, nombre: str, usuario: str, contrasena: str):
        """
        Crea el primer usuario administrador del sistema.
        Se llama desde main.py en la primera ejecución si no hay usuarios.
        """
        try:
            conn   = obtener_conexion()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO usuarios (nombre, usuario, contrasena, rol)
                VALUES (?, ?, ?, 'admin')
            """, (nombre, usuario, _hashear(contrasena)))

            conn.commit()
            conn.close()
            log.info(f"Usuario admin creado: {usuario}")

        except Exception as e:
            log.error(f"Error creando usuario admin: {e}")