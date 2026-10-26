"""
app/services/importador/mapeo.py
--------------------------------
Averigua QUÉ COLUMNA del Excel es cada dato del sistema, sin importar el orden.

El "mapeo" es un diccionario  campo → encabezado:
    {"nombre": "item", "cantidad": "cant", "referencia": "codigo"}
Los encabezados se guardan ya "normalizados" (minúsculas, sin tildes), así que
"Cant.", "CANT" y "cant" son la misma columna. Como el mapeo se basa en el
TEXTO del encabezado y no en la posición, sirve igual si en otra hoja o en otro
archivo las columnas vienen en distinto orden.

Cómo se decide (en este orden):
    1. Si el usuario ya guardó un formato (perfil) cuyas columnas están todas
       en el archivo, se usa ese.
    2. Si no, se adivina por el nombre de las columnas (ver campos.py).
    3. Lo que no se reconoce se deja sin asignar: el usuario lo elige a mano.
"""

from app.services.importador.campos import CAMPOS, CAMPOS_POR_CLAVE
from app.services.importador.lector import fila_vacia
from app.services.importador.texto import normalizar

MAX_FILAS_BUSQUEDA = 30        # cuántas filas de arriba se miran para encontrar los encabezados


def detectar_fila_encabezado(filas_previas: list[list]) -> int | None:
    """
    Busca la fila de encabezados entre las primeras filas (hay archivos con
    título o logo arriba). Gana la fila donde más columnas se reconocen.
    Retorna el número de fila (la primera es la 1) o None si no se reconoce ninguna.
    """
    reconocibles = {normalizar(s): campo.clave
                    for campo in CAMPOS for s in campo.fuertes + campo.debiles}
    mejor_fila, mejor_puntaje = None, 1                  # hacen falta al menos 2 coincidencias
    for numero, celdas in enumerate(filas_previas[:MAX_FILAS_BUSQUEDA], start=1):
        campos_vistos = {reconocibles[n] for n in map(normalizar, celdas) if n in reconocibles}
        if len(campos_vistos) > mejor_puntaje:
            mejor_fila, mejor_puntaje = numero, len(campos_vistos)
    return mejor_fila


def elegir_fila_encabezado(filas_previas: list[list], fila_indicada: int | None = None) -> int | None:
    """
    La fila de encabezados de una hoja: la que indicó el usuario; si no indicó ninguna, la
    que se detecta por el nombre de las columnas; y si tampoco se reconoce, la primera que
    tenga datos. Retorna None solo si la hoja está vacía.
    """
    if fila_indicada:
        return fila_indicada
    detectada = detectar_fila_encabezado(filas_previas)
    if detectada:
        return detectada
    return next((numero for numero, celdas in enumerate(filas_previas, start=1)
                 if not fila_vacia(celdas)), None)


def adivinar_mapeo(encabezados: list, campos=None, ocupadas=()) -> dict[str, str]:
    """
    Propone el mapeo mirando solo los nombres de las columnas.

    campos:   si se indica (lista de claves), solo se buscan esos datos; por defecto todos.
    ocupadas: posiciones de columna que NO se pueden usar (ya tienen otro dato asignado).
    """
    normales = [normalizar(h) for h in encabezados]
    buscados = [c for c in CAMPOS if campos is None or c.clave in campos]
    asignado: dict[str, int] = {}          # campo → posición de la columna
    usadas: set[int] = set(ocupadas)

    def tomar(campo_clave: str, posicion: int):
        asignado[campo_clave] = posicion
        usadas.add(posicion)

    # Pasadas 1 y 2: el encabezado es IGUAL a un nombre conocido (primero los fuertes)
    for tipo_de_nombre in ("fuertes", "debiles"):
        for campo in buscados:
            if campo.clave in asignado:
                continue
            for sinonimo in (normalizar(s) for s in getattr(campo, tipo_de_nombre)):
                posicion = next((i for i, n in enumerate(normales)
                                 if n == sinonimo and i not in usadas), None)
                if posicion is not None:
                    tomar(campo.clave, posicion)
                    break

    # Pasada 3: el encabezado CONTIENE la palabra canónica ("Cantidad (und)", "Ubicación física")
    for campo in buscados:
        if campo.clave in asignado:
            continue
        palabras = set(normalizar(campo.fuertes[0]).split())
        for i, n in enumerate(normales):
            if i not in usadas and n and palabras <= set(n.split()):
                tomar(campo.clave, i)
                break

    return {clave: normales[posicion] for clave, posicion in asignado.items()}


def mapeo_de_perfil(encabezados: list, perfiles: list[dict]) -> tuple[str | None, dict[str, str]]:
    """
    Busca un formato guardado que encaje con estas columnas: todas las columnas del
    perfil deben estar en el archivo. Si encajan varios, gana el que usa más columnas.
    Retorna (nombre del perfil, mapeo) o (None, {}).
    """
    presentes = {normalizar(h) for h in encabezados}
    encajan = [p for p in perfiles if p["mapeo"] and all(h in presentes for h in p["mapeo"].values())]
    if not encajan:
        return None, {}
    mejor = max(encajan, key=lambda p: len(p["mapeo"]))
    return mejor["nombre"], dict(mejor["mapeo"])


def proponer_mapeo(encabezados: list, perfiles: list[dict]) -> tuple[str | None, dict[str, str]]:
    """Perfil guardado si hay uno que encaje; si no, lo que se adivina por el nombre."""
    nombre, mapeo = mapeo_de_perfil(encabezados, perfiles)
    return (nombre, mapeo) if nombre else (None, adivinar_mapeo(encabezados))


def resolver_indices(encabezados: list, mapeo: dict[str, str]) -> dict[str, int]:
    """
    Convierte el mapeo en posiciones de columna para ESTA hoja:
    {"nombre": 1, "cantidad": 0}. Si una columna del mapeo no está en la hoja,
    ese campo simplemente no aparece en el resultado.
    """
    posiciones: dict[str, int] = {}
    for i, h in enumerate(encabezados):
        normal = normalizar(h)
        if not normal:
            continue
        for campo, encabezado in mapeo.items():
            if encabezado == normal and campo not in posiciones:
                posiciones[campo] = i
    return posiciones


def columnas_sin_usar(encabezados: list, mapeo: dict[str, str]) -> list[str]:
    """Encabezados (con su texto original) que NO se van a importar."""
    usados = set(mapeo.values())
    return [str(h).strip() for h in encabezados
            if normalizar(h) and normalizar(h) not in usados]


def campos_faltantes(mapeo: dict[str, str], necesita_deposito: bool = False) -> list[str]:
    """Etiquetas de los datos obligatorios que todavía no tienen columna."""
    claves = [c.clave for c in CAMPOS if c.obligatorio]
    if necesita_deposito:
        claves.append("deposito")
    return [CAMPOS_POR_CLAVE[c].etiqueta for c in claves if c not in mapeo]
