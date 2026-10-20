
from gastos.models import CodigoSATPermitido


def validar_conceptos_sat(conceptos, tipo="viatico"):
    if tipo not in ("gasto", "viatico"):
        raise ValueError("Tipo de validación no permitido")

    if not conceptos:
        return False, [{
            "codigo": "",
            "descripcion": "El CFDI no contiene conceptos",
        }]

    codigos = {
        concepto["clave"]
        for concepto in conceptos
        if concepto.get("clave")
    }

    autorizados = set(
        CodigoSATPermitido.objects.filter(
            codigo__in=codigos,
            **{tipo: True}
        ).values_list("codigo", flat=True)
    )

    rechazados = [
        {
            "codigo": concepto.get("clave", ""),
            "descripcion": concepto.get("descripcion", ""),
        }
        for concepto in conceptos
        if concepto.get("clave", "") not in autorizados
    ]

    return not rechazados, rechazados
