"""
app/services/importador/texto.py
--------------------------------
Funciones pequeñas para limpiar y comparar el texto que viene de las celdas.
"""

import re
import unicodedata

_NO_LETRAS_NI_NUMEROS = re.compile(r"[\W_]+")
_CARACTERES_INVISIBLES = dict.fromkeys(map(ord, "﻿​‌‍⁠"), None)


def normalizar(texto) -> str:
    """
    Deja el texto listo para COMPARAR: minúsculas, sin tildes, sin signos
    y con espacios simples.   "  Micrómetro (0-25)mm " → "micrometro 0 25 mm"
    Una celda vacía (None) da "".
    """
    if texto is None:
        return ""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", str(texto)) if not unicodedata.combining(c)
    )
    return _NO_LETRAS_NI_NUMEROS.sub(" ", sin_tildes.casefold()).strip()


def clave(texto) -> str:
    """
    Como `normalizar` pero sin espacios, para nombres de depósitos:
    "Depósito 1", "deposito_1" y "DEPÓSITO1" dan todos "deposito1".
    """
    return normalizar(texto).replace(" ", "")


def limpiar(valor, una_linea: bool = True) -> str | None:
    """
    Convierte el valor de una celda en texto limpio, o None si queda vacío.

    - Un número entero guardado como decimal (1.0) se escribe "1", no "1.0".
      Excel guarda así los códigos numéricos y no queremos "1.0" en la base.
    - Quita espacios duros, caracteres invisibles y espacios repetidos.
    - una_linea=False conserva los saltos de línea (para observaciones).
    """
    if valor is None:
        return None
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    texto = str(valor).translate(_CARACTERES_INVISIBLES).replace("\xa0", " ")
    if una_linea:
        texto = " ".join(texto.split())
    else:
        texto = "\n".join(" ".join(linea.split()) for linea in texto.strip().splitlines())
    return texto.strip() or None
