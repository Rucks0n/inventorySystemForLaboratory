"""
app/services/importador/analizador.py
-------------------------------------
Revisa el archivo COMPLETO antes de guardar nada. Este módulo NO escribe en la
base de datos: solo lee el archivo y dice qué filas están bien y cuáles no.

Qué comprueba en cada fila:
    nombre         obligatorio; no puede ser una fila de "Total".
    cantidad       obligatoria; entero >= 0 (ver parsear_cantidad).
    referencia, ubicación, observaciones, unidad    texto con largo máximo.
    tipo           debe ser uno de los tipos que existen en el sistema.
    depósito       debe existir (o poder crearse, si el usuario lo permitió).
    repetidos      la misma fila dos veces en el archivo.

Regla de oro: NUNCA se corrige un dato "adivinando". Si una cantidad dice
"1,5" no se redondea; se marca como error y el usuario decide. Es preferible
una fila rechazada y avisada que un dato equivocado guardado en silencio.
"""

import re

from app.services.importador import lector, mapeo as mapeo_mod
from app.services.importador.campos import CAMPOS_POR_CLAVE
from app.services.importador.catalogo import Catalogo
from app.services.importador.modelos import (
    Analisis, ConfigImportacion, ErrorImportacion, FilaValida, ImportacionCancelada, Incidencia,
)
from app.services.importador.texto import clave, limpiar, normalizar
from config.constants import (
    COMP_CONSUME, IMP_AVISO, IMP_DEPOSITO_POR_COLUMNA, IMP_DEPOSITO_POR_HOJA,
    IMP_DEPOSITO_UNICO, IMP_ERROR,
)

LARGO_MAXIMO = {"nombre": 200, "referencia": 100, "ubicacion": 100,
                "observaciones": 2000, "unidad": 30}
CANTIDAD_MAXIMA = 2_000_000_000
FILAS_DE_TOTALES = {"total", "totales", "subtotal", "suma", "gran total"}
ERRORES_DE_EXCEL = {"#n/a", "#ref!", "#value!", "#div/0!", "#name?", "#null!", "#num!", "#####"}
FILAS_POR_AVISO_DE_PROGRESO = 500


# ─────────────────────────────────────────────────────────────────────────────
#  Cantidades
# ─────────────────────────────────────────────────────────────────────────────

def parsear_cantidad(valor) -> tuple[int | None, str | None]:
    """
    Convierte la celda de cantidad en un entero.
    Retorna (número, None) si está bien, o (None, "motivo del error").

    No se adivina nada: "1,5" y "1.000" son ambiguos (¿decimal o miles?) y se rechazan.
    """
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None, "está vacía"
    if isinstance(valor, bool):
        return None, "no es un número"

    if isinstance(valor, int):
        numero = valor
    elif isinstance(valor, float):
        if valor != valor or valor in (float("inf"), float("-inf")):
            return None, "no es un número válido"
        if not valor.is_integer():
            return None, (f"tiene decimales ({valor:g}); por ahora solo se aceptan cantidades "
                          "enteras (usa una unidad más pequeña, por ejemplo mL en vez de L)")
        numero = int(valor)
    elif isinstance(valor, str):
        texto = valor.strip().replace("\xa0", "")
        if re.fullmatch(r"\d+", texto):
            numero = int(texto)
        elif re.fullmatch(r"\d{1,3}([.,]\d{3})+", texto):
            return None, (f"«{texto}» es ambiguo (¿{texto.replace('.', ',')} con decimales o "
                          "un número con separador de miles?); escríbelo sin punto ni coma")
        elif re.fullmatch(r"\d+[.,]0+", texto):
            numero = int(texto.replace(",", ".").split(".")[0])
        elif re.fullmatch(r"\d+[.,]\d+", texto):
            return None, (f"tiene decimales («{texto}»); por ahora solo se aceptan cantidades "
                          "enteras")
        else:
            return None, (f"no es un número («{texto}»); escribe solo el número y pon la "
                          "unidad en su propia columna")
    else:
        return None, "no es un número"

    if numero < 0:
        return None, "es negativa"
    if numero > CANTIDAD_MAXIMA:
        return None, "es demasiado grande"
    return numero, None


# ─────────────────────────────────────────────────────────────────────────────
#  Estado compartido durante el análisis
# ─────────────────────────────────────────────────────────────────────────────

class _Estado:
    def __init__(self, config: ConfigImportacion, catalogo: Catalogo, progreso, cancelado):
        self.config = config
        self.catalogo = catalogo
        self.progreso = progreso
        self.cancelado = cancelado
        self.analisis = Analisis(config=config)
        self.vistos: dict[tuple, tuple[str, int]] = {}      # fila repetida → (hoja, fila) donde apareció
        self._depositos_nuevos: dict[str, str] = {}         # clave → nombre
        self._tipo_defecto = catalogo.tipos_por_id.get(config.tipo_defecto_id)

    def revisar_cancelacion(self):
        if self.cancelado and self.cancelado():
            raise ImportacionCancelada()

    def avisar_progreso(self, hoja: str):
        if self.progreso:
            self.progreso(f"Revisando «{hoja}»…", self.analisis.leidas, None)

    def problema(self, hoja, fila, nivel, campo, mensaje):
        self.analisis.incidencias.append(Incidencia(hoja, fila, nivel, campo, mensaje))

    def hoja_omitida(self, hoja, motivo):
        self.problema(hoja, 0, IMP_ERROR, None, f"La hoja «{hoja}» no se importó: {motivo}")

    def resolver_deposito(self, nombre) -> str | None:
        """
        Nombre oficial del depósito, o None si no existe y no se pueden crear.
        "Depósito 1", "deposito1" y "DEPÓSITO_1" se consideran el mismo depósito.
        """
        nombre = limpiar(nombre)
        if not nombre:
            return None
        existente = self.catalogo.depositos.get(clave(nombre))
        if existente:
            return existente[1]
        if not self.config.crear_depositos:
            return None
        return self._depositos_nuevos.setdefault(clave(nombre), nombre)

    def tipo_efectivo(self, tipo_id):
        """El tipo de la fila, o el tipo por defecto si la fila no trae uno."""
        return self.catalogo.tipos_por_id.get(tipo_id) if tipo_id else self._tipo_defecto


# ─────────────────────────────────────────────────────────────────────────────
#  Análisis
# ─────────────────────────────────────────────────────────────────────────────

def analizar(config: ConfigImportacion, catalogo: Catalogo,
             progreso=None, cancelado=None) -> Analisis:
    """
    Revisa todas las hojas elegidas.

    progreso(mensaje, filas_leidas, total_o_None) — para mostrar avance (opcional)
    cancelado() → True si el usuario canceló (opcional)

    Lanza ErrorImportacion si el archivo no se puede leer o la configuración está incompleta.
    """
    if not config.hojas:
        raise ErrorImportacion("No hay ninguna hoja seleccionada para importar.")
    faltan = mapeo_mod.campos_faltantes(config.mapeo, config.modo_deposito == IMP_DEPOSITO_POR_COLUMNA)
    if faltan:
        raise ErrorImportacion("Falta indicar la columna de: " + ", ".join(faltan) + ".")
    if config.modo_deposito == IMP_DEPOSITO_UNICO and not limpiar(config.deposito_unico):
        raise ErrorImportacion("Elige el depósito donde se guardarán todos los ítems.")

    estado = _Estado(config, catalogo, progreso, cancelado)
    with lector.Archivo(config.ruta) as archivo:        # se abre UNA vez para todas las hojas
        for hoja in config.hojas:
            estado.revisar_cancelacion()
            _analizar_hoja(hoja, estado, archivo)

    estado.analisis.depositos_nuevos = list(estado._depositos_nuevos.values())
    return estado.analisis


def _analizar_hoja(hoja: str, est: _Estado, archivo: lector.Archivo):
    cfg, ana = est.config, est.analisis

    # 1. Depósito de la hoja (cuando no viene en una columna)
    deposito_fijo = None
    if cfg.modo_deposito != IMP_DEPOSITO_POR_COLUMNA:
        nombre = hoja if cfg.modo_deposito == IMP_DEPOSITO_POR_HOJA else cfg.deposito_unico
        deposito_fijo = est.resolver_deposito(nombre)
        if deposito_fijo is None:
            est.hoja_omitida(hoja, f"el depósito «{limpiar(nombre)}» no existe. Pide a un "
                                   "administrador que lo cree o activa «Crear los depósitos que falten».")
            return

    # 2. Encabezados de la hoja
    previa = archivo.previa(hoja, max(40, cfg.fila_encabezado or 0))
    fila_enc = mapeo_mod.elegir_fila_encabezado(previa, cfg.fila_encabezado)
    if fila_enc is None:
        est.hoja_omitida(hoja, "está vacía.")
        return
    if fila_enc > len(previa):
        est.hoja_omitida(hoja, f"termina antes de la fila de encabezados ({fila_enc}).")
        return
    encabezados = previa[fila_enc - 1]
    ana.encabezados[hoja] = encabezados

    # La columna de depósito solo cuenta si el depósito se lee de ahí
    mapeo = {c: h for c, h in cfg.mapeo.items() if not (c == "deposito" and deposito_fijo is not None)}
    indices = mapeo_mod.resolver_indices(encabezados, mapeo)
    con_otro_nombre = _buscar_columnas_con_otro_nombre(hoja, encabezados, mapeo, indices)
    sin_columna = []
    for campo, encabezado in mapeo.items():
        if campo not in indices:
            etiqueta = CAMPOS_POR_CLAVE[campo].etiqueta
            if CAMPOS_POR_CLAVE[campo].obligatorio or campo == "deposito":
                est.hoja_omitida(hoja, f"no tiene la columna «{encabezado}» ({etiqueta}). "
                                       f"Los encabezados están en la fila {fila_enc}.")
                return
            sin_columna.append(f"«{encabezado}» ({etiqueta})")

    # Avisos (una sola vez por hoja, y solo si la hoja sigue adelante)
    if sin_columna:
        est.problema(hoja, 0, IMP_AVISO, None,
                     f"La hoja «{hoja}» no tiene estas columnas: {', '.join(sin_columna)}. "
                     "Esos datos quedan vacíos en esta hoja.")
    for campo, mensaje in con_otro_nombre:
        est.problema(hoja, 0, IMP_AVISO, campo, mensaje)

    # 3. Filas
    ultimo_deposito = None
    for numero, valores in archivo.filas(hoja, fila_enc + 1):
        ana.leidas += 1
        if ana.leidas % FILAS_POR_AVISO_DE_PROGRESO == 0:
            est.revisar_cancelacion()
            est.avisar_progreso(hoja)

        deposito = deposito_fijo
        if deposito is None:                                   # depósito en una columna
            celda = valores[indices["deposito"]] if indices["deposito"] < len(valores) else None
            texto = limpiar(celda)
            if texto:
                ultimo_deposito = texto                        # celdas combinadas: se arrastra hacia abajo
            deposito = ultimo_deposito
        _revisar_fila(est, hoja, numero, valores, indices, deposito)


def _buscar_columnas_con_otro_nombre(hoja: str, encabezados: list, mapeo: dict[str, str],
                                     indices: dict[str, int]) -> list[tuple[str, str]]:
    """
    En un Excel con varias hojas escritas a mano, la misma columna puede llamarse distinto
    ("Item" en una hoja y "Nombre" en otra). Si a esta hoja le falta el encabezado que el
    usuario eligió, se busca esa columna por nombre, igual que hizo el asistente al
    proponerla. Nunca se toma una columna que ya sirve para otro dato, y siempre se avisa
    para que el usuario lo vea en la revisión.

    Completa `indices` y retorna los avisos [(campo, mensaje)] que hay que registrar.
    """
    faltan = [campo for campo in mapeo if campo not in indices]
    if not faltan:
        return []
    avisos = []
    propuesta = mapeo_mod.adivinar_mapeo(encabezados, campos=faltan, ocupadas=set(indices.values()))
    for campo, posicion in mapeo_mod.resolver_indices(encabezados, propuesta).items():
        if posicion in indices.values():
            continue
        indices[campo] = posicion
        avisos.append((campo, f"En la hoja «{hoja}» la columna de {CAMPOS_POR_CLAVE[campo].etiqueta} "
                              f"se llama «{str(encabezados[posicion]).strip()}» (en el resto "
                              f"«{mapeo[campo]}»); se usó esa. Revisa que sea la correcta."))
    return avisos


# ─────────────────────────────────────────────────────────────────────────────
#  Revisión de una fila
# ─────────────────────────────────────────────────────────────────────────────

def _revisar_fila(est: _Estado, hoja: str, numero: int, valores: list,
                  indices: dict[str, int], deposito: str | None):
    problemas: list[tuple[str, str | None, str]] = []          # (nivel, campo, mensaje)

    def celda(campo):
        i = indices.get(campo)
        return valores[i] if i is not None and i < len(valores) else None

    def error(campo, mensaje):
        problemas.append((IMP_ERROR, campo, mensaje))

    def aviso(campo, mensaje):
        problemas.append((IMP_AVISO, campo, mensaje))

    def texto(campo):
        """Texto limpio del campo; comprueba el largo máximo."""
        valor = limpiar(celda(campo), una_linea=(campo != "observaciones"))
        if valor and len(valor) > LARGO_MAXIMO[campo]:
            error(campo, f"{CAMPOS_POR_CLAVE[campo].etiqueta} demasiado largo "
                         f"({len(valor)} caracteres; el máximo es {LARGO_MAXIMO[campo]}).")
            return None
        return valor

    # Celdas con error de Excel (#REF!, #N/A...) en cualquier columna que se vaya a usar
    for campo in indices:
        valor = celda(campo)
        if isinstance(valor, str) and valor.strip().lower() in ERRORES_DE_EXCEL:
            error(campo, f"La celda de «{CAMPOS_POR_CLAVE[campo].etiqueta}» tiene un error de "
                         f"Excel ({valor.strip()}). Corrígela en el archivo.")

    nombre = texto("nombre")
    if not nombre:
        if not any(c == "nombre" for _, c, _ in problemas):
            error("nombre", "Falta el nombre del ítem.")
    elif normalizar(nombre) in FILAS_DE_TOTALES:
        error("nombre", "Parece una fila de totales; no se importa.")

    cantidad = None
    if not any(c == "cantidad" for _, c, _ in problemas):
        cantidad, motivo = parsear_cantidad(celda("cantidad"))
        if motivo:
            error("cantidad", f"La cantidad {motivo}.")

    referencia = texto("referencia")
    ubicacion = texto("ubicacion")
    observaciones = texto("observaciones")
    unidad = texto("unidad")

    tipo_id = None
    valor_tipo = limpiar(celda("tipo"))
    if valor_tipo:
        tipo = est.catalogo.tipos.get(normalizar(valor_tipo))
        if tipo:
            tipo_id = tipo.id
        else:
            error("tipo", f"El tipo «{valor_tipo}» no existe. Tipos válidos: "
                          f"{', '.join(est.catalogo.nombres_de_tipos()) or '(ninguno)'}.")

    tipo_final = est.tipo_efectivo(tipo_id)
    if tipo_final and tipo_final.comportamiento == COMP_CONSUME and not unidad:
        aviso("unidad", f"«{tipo_final.nombre}» sin unidad de medida (¿mL, g, unidades?).")

    nombre_deposito = None
    if deposito is None:
        error("deposito", "Falta el depósito.")
    else:
        nombre_deposito = est.resolver_deposito(deposito)
        if nombre_deposito is None:
            error("deposito", f"El depósito «{deposito}» no existe. Pide a un administrador "
                              "que lo cree o activa «Crear los depósitos que falten».")

    # Repetidos dentro del archivo: mismo depósito, nombre y referencia
    if not any(nivel == IMP_ERROR for nivel, _, _ in problemas):
        llave = (clave(nombre_deposito), normalizar(nombre), normalizar(referencia))
        antes = est.vistos.get(llave)
        if antes:
            error("nombre", f"Repetido: es igual a la fila {antes[1]}"
                            f"{'' if antes[0] == hoja else f' de la hoja «{antes[0]}»'} "
                            "(mismo depósito, nombre y referencia). Si son ítems distintos, "
                            "diferéncialos en la referencia; si es el mismo, suma sus cantidades.")
        else:
            est.vistos[llave] = (hoja, numero)

    ana = est.analisis
    for nivel, campo, mensaje in problemas:
        est.problema(hoja, numero, nivel, campo, mensaje)
    if problemas:
        ana.originales[(hoja, numero)] = list(valores)
    if not any(nivel == IMP_ERROR for nivel, _, _ in problemas):
        ana.filas.append(FilaValida(
            hoja=hoja, fila=numero, deposito=nombre_deposito, nombre=nombre, cantidad=cantidad,
            referencia=referencia, ubicacion=ubicacion, observaciones=observaciones,
            tipo_id=tipo_id, unidad=unidad,
        ))
