"""
app/utils/validators.py
------------------------
Funciones de validación reutilizables.
Úsalas en los controllers antes de guardar datos en la BD.

Todas retornan (True, "") si el dato es válido,
o (False, "mensaje de error") si no lo es.
"""


def validar_campo_requerido(valor: str, nombre_campo: str):
    """Verifica que un campo de texto no esté vacío."""
    if not valor or not str(valor).strip():
        return False, f"El campo '{nombre_campo}' es obligatorio."
    return True, ""


def validar_numero_positivo(valor, nombre_campo: str):
    """Verifica que el valor sea un número mayor o igual a cero."""
    try:
        numero = float(valor)
        if numero < 0:
            return False, f"'{nombre_campo}' debe ser un valor positivo."
        return True, ""
    except (ValueError, TypeError):
        return False, f"'{nombre_campo}' debe ser un número válido."


def validar_longitud(valor: str, nombre_campo: str, minimo=1, maximo=100):
    """Verifica que un texto tenga una longitud dentro del rango permitido."""
    largo = len(str(valor).strip())
    if largo < minimo:
        return False, f"'{nombre_campo}' debe tener al menos {minimo} caracteres."
    if largo > maximo:
        return False, f"'{nombre_campo}' no puede superar {maximo} caracteres."
    return True, ""


def validar_formulario(campos: dict):
    """
    Valida múltiples campos de un formulario de una sola vez.

    Parámetro:
        campos: diccionario con { nombre_campo: valor }

    Retorna:
        (True, "")  si todo es válido
        (False, "primer mensaje de error encontrado")

    Ejemplo de uso en un controller:
        valido, mensaje = validar_formulario({
            "Nombre":   nombre,
            "Cantidad": cantidad,
        })
        if not valido:
            mostrar_error(mensaje)
            return
    """
    for nombre, valor in campos.items():
        ok, msg = validar_campo_requerido(valor, nombre)
        if not ok:
            return False, msg
    return True, ""