"""
app/utils/validators.py
------------------------
Funciones de validación reutilizables para formularios.
Úsalas en los controllers antes de guardar datos en la BD.

Todas retornan (True, "") si el dato es válido,
o (False, "mensaje de error") si no lo es.
"""


def campo_requerido(valor, nombre_campo: str) -> tuple[bool, str]:
    """Verifica que un campo de texto no esté vacío."""
    if valor is None or str(valor).strip() == "":
        return False, f"El campo '{nombre_campo}' es obligatorio."
    return True, ""


def numero_positivo(valor, nombre_campo: str) -> tuple[bool, str]:
    """Verifica que el valor sea un número mayor o igual a cero."""
    try:
        if float(valor) < 0:
            return False, f"'{nombre_campo}' debe ser un valor positivo."
        return True, ""
    except (ValueError, TypeError):
        return False, f"'{nombre_campo}' debe ser un número válido."


def numero_entero_positivo(valor, nombre_campo: str) -> tuple[bool, str]:
    """Verifica que el valor sea un entero >= 1."""
    try:
        n = int(valor)
        if n < 1:
            return False, f"'{nombre_campo}' debe ser al menos 1."
        return True, ""
    except (ValueError, TypeError):
        return False, f"'{nombre_campo}' debe ser un número entero válido."


def longitud(valor: str, nombre_campo: str, minimo: int = 1, maximo: int = 200) -> tuple[bool, str]:
    """Verifica longitud de texto dentro de rango permitido."""
    largo = len(str(valor).strip())
    if largo < minimo:
        return False, f"'{nombre_campo}' debe tener al menos {minimo} caracteres."
    if largo > maximo:
        return False, f"'{nombre_campo}' no puede superar {maximo} caracteres."
    return True, ""


def correo(valor: str) -> tuple[bool, str]:
    """Validación básica de formato de correo electrónico."""
    v = str(valor).strip()
    if "@" not in v or "." not in v.split("@")[-1]:
        return False, "El correo electrónico no tiene un formato válido."
    return True, ""


def formulario(campos: dict) -> tuple[bool, str]:
    """
    Valida múltiples campos requeridos de un formulario de una sola vez.

    Parámetro:
        campos: { "Nombre del campo": valor, ... }

    Retorna (True, "") si todo es válido,
    o (False, "primer mensaje de error encontrado").

    Ejemplo de uso en un controller:
        ok, msg = validators.formulario({
            "Nombre":   datos.get("nombre"),
            "Cantidad": datos.get("cantidad"),
        })
        if not ok:
            return False, msg
    """
    for nombre, valor in campos.items():
        ok, msg = campo_requerido(valor, nombre)
        if not ok:
            return False, msg
    return True, ""
