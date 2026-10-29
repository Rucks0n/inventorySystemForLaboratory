"""
tests/test_conexiones.py
------------------------
Protege contra el error «database is locked».

Qué pasaba: si una operación fallaba a mitad de camino (por ejemplo, eliminar un
ítem que ya tuvo préstamos), su conexión a la base quedaba ABIERTA con la escritura
a medias. Desde ese momento todo lo demás esperaba 5 segundos y fallaba con
«database is locked», hasta cerrar el programa.

Estas pruebas comprueban que, pase lo que pase, ninguna conexión se queda abierta.
"""

import sqlite3
import time
from unittest import mock

from app.controllers.docentes_controller import DocentesController, UsuariosController
from app.controllers.inventario_controller import DepositosController, InventarioController
from app.controllers.prestamos_controller import PrestamosController
from app.controllers.tipos_controller import TiposController
from db import database
from db.database import conexion
from db.migraciones import aplicar_pendientes
from tests.base_prueba import BaseConBD


def esta_cerrada(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1")
    except sqlite3.ProgrammingError:          # «Cannot operate on a closed database»
        return True
    return False


class PruebasConexion(BaseConBD):
    """La función conexion() de db/database.py."""

    def setUp(self):
        super().setUp()
        aplicar_pendientes()

    def test_se_cierra_al_terminar_bien(self):
        with conexion() as conn:
            conn.execute("SELECT 1")
        self.assertTrue(esta_cerrada(conn))

    def test_se_cierra_aunque_ocurra_un_error_y_el_error_sigue_su_camino(self):
        with self.assertRaises(ZeroDivisionError):
            with conexion() as conn:
                1 / 0
        self.assertTrue(esta_cerrada(conn))

    def test_lo_que_no_se_guardo_con_commit_se_descarta(self):
        with self.assertRaises(RuntimeError):
            with conexion() as conn:
                conn.execute("INSERT INTO depositos (nombre) VALUES ('A medias')")
                raise RuntimeError("falló antes del commit")
        self.assertEqual(self.consulta("SELECT COUNT(*) AS n FROM depositos")[0]["n"], 0)

    def test_lo_que_si_se_guardo_con_commit_queda(self):
        with conexion() as conn:
            conn.execute("INSERT INTO depositos (nombre) VALUES ('Guardado')")
            conn.commit()
        self.assertEqual(self.consulta("SELECT nombre FROM depositos")[0]["nombre"], "Guardado")


class PruebasSinBloqueos(BaseConBD):
    """Los controladores nunca dejan la base bloqueada, ni siquiera cuando fallan."""

    def setUp(self):
        super().setUp()
        aplicar_pendientes()
        self.dep, self.inv = DepositosController(), InventarioController()
        self.pre, self.tipos = PrestamosController(), TiposController()
        self.docentes, self.usuarios = DocentesController(), UsuariosController()

        self.dep.agregar({"nombre": "Lab"})
        self.inv.agregar_item({"deposito_id": 1, "nombre": "Sensor", "cantidad_total": 5})
        self.inv.agregar_item({"deposito_id": 1, "nombre": "Pesa", "cantidad_total": 2})
        self.ejecutar("INSERT INTO usuarios (nombre, codigo, rol, contrasena) VALUES ('Ana','A1','usuario','x')")
        self.pre.registrar_prestamo({"item_id": 1, "usuario_id": 1, "cantidad": 1})
        self.pre.registrar_devolucion(1)                 # el «Sensor» ya tiene historial

    def registrar_conexiones(self) -> list:
        """Anota cada conexión que se abra, para comprobar después que se cerraron."""
        abiertas, original = [], database.obtener_conexion

        def registrar():
            conn = original()
            abiertas.append(conn)
            return conn

        self.enterContext(mock.patch.object(database, "obtener_conexion", registrar))
        return abiertas

    # ── el caso que reportó el usuario ─────────────────────────────────────

    def test_un_fallo_al_eliminar_no_bloquea_lo_siguiente(self):
        self.pre.registrar_prestamo({"item_id": 1, "usuario_id": 1, "cantidad": 1})     # préstamo activo
        ok, msg = self.inv.eliminar_item(1)
        self.assertFalse(ok)
        self.assertIn("préstamos activos", msg)

        inicio = time.time()
        self.assertEqual(self.inv.agregar_item({"deposito_id": 1, "nombre": "Nuevo", "cantidad_total": 1}), (True, ""))
        self.assertEqual(self.inv.eliminar_item(2), (True, ""))
        self.assertLess(time.time() - inicio, 2, "algo quedó bloqueando la base")

    def test_no_se_elimina_un_item_con_prestamo_activo(self):
        self.pre.registrar_prestamo({"item_id": 2, "usuario_id": 1, "cantidad": 1})
        ok, msg = self.inv.eliminar_item(2)
        self.assertFalse(ok)
        self.assertIn("préstamos activos", msg)

    def test_eliminar_un_item_que_no_existe(self):
        self.assertEqual(self.inv.eliminar_item(999), (False, "Ítem no encontrado."))

    # ── ninguna conexión queda abierta, tampoco cuando hay errores ─────────

    def test_ningun_error_deja_una_conexion_abierta(self):
        abiertas = self.registrar_conexiones()
        casos = {
            "depósito repetido":              lambda: self.dep.agregar({"nombre": "Lab"}),
            "renombrar a un depósito que ya existe": lambda: (self.dep.agregar({"nombre": "Otro"}),
                                                              self.dep.editar(2, {"nombre": "Lab"})),
            "eliminar un depósito con ítems": lambda: self.dep.eliminar(1),
            "ítem en un depósito inexistente": lambda: self.inv.agregar_item(
                {"deposito_id": 999, "nombre": "X", "cantidad_total": 1}),
            "editar un ítem inexistente":     lambda: self.inv.editar_item(999, {"nombre": "X", "cantidad_total": 1}),
            "eliminar un ítem con préstamo activo": lambda: (
                self.pre.registrar_prestamo({"item_id": 2, "usuario_id": 1, "cantidad": 1}),
                self.inv.eliminar_item(2)),
            "eliminar un ítem con historial": lambda: self.inv.eliminar_item(1),
            "eliminar un ítem inexistente":   lambda: self.inv.eliminar_item(999),
            "préstamo a un usuario inexistente (falla al guardar)": lambda: self.pre.registrar_prestamo(
                {"item_id": 2, "usuario_id": 999, "cantidad": 1}),
            "préstamo sin stock":             lambda: self.pre.registrar_prestamo(
                {"item_id": 2, "usuario_id": 1, "cantidad": 99}),
            "devolver un préstamo que no existe": lambda: self.pre.registrar_devolucion(999),
            "docente con correo repetido":    lambda: (
                self.docentes.agregar({"nombre": "Luis", "correo": "luis@u.co"}),
                self.docentes.agregar({"nombre": "Luis 2", "correo": "luis@u.co"})),
            "usuario con código repetido":    lambda: self.usuarios.agregar({"nombre": "Ana 2", "codigo": "A1"}),
            "tipo de ítem repetido":          lambda: self.tipos.agregar({"nombre": "Consumible", "comportamiento": "consume"}),
            "consultas":                      lambda: (self.dep.obtener_todos(), self.inv.obtener_todos_los_items(),
                                                       self.inv.buscar_items("s"), self.pre.obtener_activos(),
                                                       self.pre.obtener_historial(), self.docentes.obtener_todos(),
                                                       self.usuarios.buscar("a"), self.tipos.obtener_todos()),
        }
        for nombre, caso in casos.items():
            with self.subTest(nombre):
                antes = len(abiertas)
                caso()
                self.assertGreater(len(abiertas), antes, "la prueba no llegó a abrir la base")
                sin_cerrar = [c for c in abiertas[antes:] if not esta_cerrada(c)]
                self.assertEqual(sin_cerrar, [], "quedó una conexión abierta")

    def test_otra_conexion_puede_escribir_despues_de_cualquier_error(self):
        """La señal real del problema: ¿alguien más puede escribir?"""
        self.pre.registrar_prestamo({"item_id": 2, "usuario_id": 1, "cantidad": 1})
        self.inv.eliminar_item(2)                       # falla: tiene un préstamo activo
        self.pre.registrar_prestamo({"item_id": 2, "usuario_id": 999, "cantidad": 1})
        self.docentes.agregar({"nombre": "A", "correo": "a@u.co"})
        self.docentes.agregar({"nombre": "B", "correo": "a@u.co"})
        otra = sqlite3.connect(self.ruta_bd, timeout=0.2)
        try:
            otra.execute("BEGIN IMMEDIATE")           # pide el permiso de escritura: falla si alguien lo retiene
            otra.rollback()
        finally:
            otra.close()
