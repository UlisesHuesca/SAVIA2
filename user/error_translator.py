from django.db import IntegrityError, OperationalError
from django.core.exceptions import (
    ValidationError,
    PermissionDenied,
)
from django.http import Http404
import re





def obtener_codigo_mysql(exception):
    """
    Obtiene el código numérico de error de MySQL.
    Por ejemplo: 1062 para duplicidad.
    """
    args = getattr(exception, "args", ())

    if args and isinstance(args[0], int):
        return args[0]

    causa = getattr(exception, "__cause__", None)

    if causa:
        args = getattr(causa, "args", ())
        if args and isinstance(args[0], int):
            return args[0]

    return None

def obtener_referencia_error(exception):
    """
    Ejemplo:
    dashboard_order.folio -> DO_folio
    """

    mensaje = str(exception)

    coincidencia = re.search(
        r"for key ['`\"]([^'`\"]+)['`\"]",
        mensaje,
        flags=re.IGNORECASE,
    )

    if not coincidencia:
        return "N/D"

    restriccion = coincidencia.group(1)
    partes = restriccion.split(".")

    if len(partes) != 2:
        return "N/D"

    tabla, campo = partes

    segmentos = tabla.split("_")

    codigo_tabla = "".join(
        segmento[0].upper()
        for segmento in segmentos
        if segmento
    )

    # Solo permitir identificadores sencillos
    if not re.fullmatch(r"[A-Za-z0-9_]+", campo):
        return "N/D"

    return f"{codigo_tabla}_{campo}"


def traducir_error(exception, request=None):

    codigo_mysql = obtener_codigo_mysql(exception)

    resultado = {
        "tipo": "Error interno",
        "detalle": (
            "Se presentó un problema inesperado "
            "al procesar la operación."
        ),
        "referencia": "N/D",
    }

    if isinstance(exception, IntegrityError):

        if codigo_mysql == 1062:
            resultado.update({
                "tipo": "Registro duplicado",
                "detalle": (
                    "Ya existe un registro con uno de "
                    "los valores que intentas guardar."
                ),
                "referencia": obtener_referencia_error(exception),
            })

        elif codigo_mysql == 1451:
            resultado.update({
                "tipo": "Registro relacionado",
                "detalle": (
                    "No es posible eliminar o modificar "
                    "el registro porque tiene información relacionada."
                ),
            })

        elif codigo_mysql == 1452:
            resultado.update({
                "tipo": "Relación no válida",
                "detalle": (
                    "No fue posible guardar la información "
                    "porque una relación no es válida."
                ),
            })

        elif codigo_mysql == 1048:
            resultado.update({
                "tipo": "Campo obligatorio",
                "detalle": (
                    "Falta información necesaria para "
                    "guardar el registro."
                ),
            })

        else:
            resultado.update({
                "tipo": "Error de integridad",
                "detalle": (
                    "No fue posible guardar la información "
                    "debido a una restricción de integridad."
                ),
            })

    elif isinstance(exception, OperationalError):
        resultado.update({
            "tipo": "Error de base de datos",
            "detalle": (
                "No fue posible completar la operación "
                "debido a un problema en el procesamiento de datos."
            ),
        })

    elif isinstance(exception, ValidationError):
        resultado.update({
            "tipo": "Error de validación",
            "detalle": (
                "La información no cumple con las "
                "validaciones requeridas."
            ),
        })

    return resultado