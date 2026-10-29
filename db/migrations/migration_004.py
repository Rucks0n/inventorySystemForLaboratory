"""
db/migrations/migration_004.py
------------------------------
Permite ELIMINAR un ítem que ya tiene historial, sin perder el historial.

Antes, borrar un ítem con movimientos fallaba (clave foránea). Ahora:

  1. El historial (tabla movimientos) guarda también el NOMBRE y la REFERENCIA del
     ítem (columnas item_nombre / item_referencia), para poder mostrarlo aunque el
     ítem ya no exista.
  2. Un disparador (trigger) se encarga de todo al borrar un ítem:
       - copia su nombre y referencia a sus movimientos y los desvincula (item_id = NULL);
       - borra sus préstamos ya devueltos y sus devoluciones (el detalle de esos
         movimientos queda en el historial). Si tuviera un préstamo ACTIVO no se
         borra nada: la base lo impide.

Así el inventario no se llena de ítems que ya no están, y el historial sigue completo.
"""

from db.database  import obtener_conexion
from app.utils.logger import log
from config.constants import PRESTAMO_ACTIVO


def ejecutar():
    conn = obtener_conexion()
    try:
        conn.execute("BEGIN")

        columnas = {fila["name"] for fila in conn.execute("PRAGMA table_info(movimientos)")}
        if "item_nombre" not in columnas:
            conn.execute("ALTER TABLE movimientos ADD COLUMN item_nombre TEXT")
        if "item_referencia" not in columnas:
            conn.execute("ALTER TABLE movimientos ADD COLUMN item_referencia TEXT")

        conn.execute(f"""
            CREATE TRIGGER IF NOT EXISTS items_antes_de_eliminar
            BEFORE DELETE ON items
            BEGIN
                UPDATE movimientos
                SET    item_nombre = OLD.nombre, item_referencia = OLD.referencia, item_id = NULL
                WHERE  item_id = OLD.id;
                DELETE FROM devoluciones WHERE item_id = OLD.id;
                DELETE FROM prestamos    WHERE item_id = OLD.id AND estado <> '{PRESTAMO_ACTIVO}';
            END
        """)

        conn.commit()
        log.info("Migración 004 ejecutada: historial conserva los ítems eliminados.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
