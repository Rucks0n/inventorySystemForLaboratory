"""
app/ui/importar/
----------------
El asistente de importación de inventario (la parte visual).
La lógica de verdad (leer, revisar y guardar) está en app/services/importador/;
aquí solo se muestran las pantallas.

    dialogo.py          la ventana y la navegación entre pasos
    base.py             estado compartido y clase base de los pasos
    paso_archivo.py     1. elegir archivo y hojas
    paso_columnas.py    2. qué columna es cada dato
    paso_destino.py     3. depósitos, tipo por defecto y qué hacer con los repetidos
    paso_revision.py    4. revisar todo antes de guardar
    paso_resultado.py   5. guardar y mostrar el resultado
    hilos.py            trabajos en segundo plano (para que la ventana no se congele)

Uso:
    dlg = ImportarDialog(parent=self)
    dlg.exec()
    if dlg.hubo_cambios:
        ...recargar la pantalla...
"""

from app.ui.importar.dialogo import ImportarDialog

__all__ = ["ImportarDialog"]
