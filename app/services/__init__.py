"""
app/services/importador/
------------------------
Importa un inventario desde un archivo Excel (.xlsx) o CSV a la base de datos.

El trabajo está dividido en piezas pequeñas. Cada archivo hace UNA cosa, así
que si algo falla o hay que ajustarlo, se sabe dónde mirar:

    texto.py          Limpia y compara texto de celdas (tildes, mayúsculas, espacios).
    campos.py         Qué información maneja el sistema y cómo suelen llamarse sus columnas.
    modelos.py        Los "paquetes de datos" que viajan entre las piezas.
    catalogo.py       Lee de la base lo que hace falta para validar (depósitos y tipos).
    lector.py         Lee el archivo fila por fila, sin cargarlo entero en memoria.
    mapeo.py          Adivina qué columna es cuál, sin importar el orden.
    perfiles.py       Guarda los formatos de columnas que el usuario ya configuró.
    analizador.py     Revisa cada fila ANTES de guardar nada (no toca la base).
    ejecutor.py       Guarda en la base: copia de seguridad + una sola transacción.
    reporte_errores.py  Genera el Excel con los problemas encontrados.
    plantilla.py      Genera la plantilla de Excel descargable.

Recorrido normal (lo hace app/ui/importar_dialog.py):

    lector.listar_hojas()  →  mapeo.proponer_mapeo()  →  analizador.analizar()
         →  ejecutor.simular()  (vista previa, no guarda)
         →  ejecutor.ejecutar() (guarda, o no guarda NADA si algo falla)

Nada en esta carpeta importa PyQt: se puede probar y usar sin ventanas.
"""
