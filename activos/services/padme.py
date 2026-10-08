from collections import defaultdict
import requests
from django.conf import settings
from dashboard.models import Activo
import re
import unicodedata



def normalizar_eco(valor):
    if valor is None:
        return ""

    eco = unicodedata.normalize("NFKC", str(valor))
    eco = eco.strip().upper()

    # Unificar guiones
    eco = re.sub(r"[‐-‒–—−]", "-", eco)

    # Prefijos conocidos de distrito
    prefijos = ["VHSA", "PZR", "ALT", "VDT", "VZR"]

    patron = rf"^(?:{'|'.join(prefijos)})[\s.\-_]*"

    eco = re.sub(patron, "", eco)

    # Eliminar espacios internos
    eco = re.sub(r"\s+", "", eco)

    # Unificar guiones consecutivos
    eco = re.sub(r"-+", "-", eco)

    # Normalizar económicos UBM:
    # U202, U-202, U--0202, U00202
    match = re.fullmatch(r"U-?(\d+)", eco)

    if match:
        numero = int(match.group(1))
        return f"U-{numero}"

    return eco


def conciliar_activos_padme():

    response = requests.get(
        settings.PADME_API_URL,
        headers={
            "Authorization": f"Token {settings.PADME_API_TOKEN}",
            "Accept": "application/json",
        },
        timeout=30,
    )

    response.raise_for_status()
    datos_padme = response.json()

    if not isinstance(datos_padme, list):
        raise ValueError(
            "La respuesta de PADME no contiene una lista de activos."
        )

    activos_savia = Activo.objects.filter(
        categoria__nombre="UBM"
    ).exclude(
        eco_unidad__isnull=True
    ).exclude(
        eco_unidad=""
    ).values(
        "id",
        "eco_unidad",
        "activo__distrito__nombre",
        "estatus__nombre",
    )

    savia_por_eco = defaultdict(list)
    padme_por_eco = defaultdict(list)

    for activo in activos_savia:
        eco = normalizar_eco(activo["eco_unidad"])
        if eco:
            savia_por_eco[eco].append(activo)

    for activo in datos_padme:
        eco = normalizar_eco(activo.get("serial"))
        if eco:
            padme_por_eco[eco].append(activo)

    resultados = []

    todos_los_ecos = sorted(
        set(savia_por_eco) | set(padme_por_eco)
    )

    for eco in todos_los_ecos:

        registros_savia = savia_por_eco.get(eco, [])
        registros_padme = padme_por_eco.get(eco, [])

        savia = registros_savia[0] if registros_savia else {}
        padme = registros_padme[0] if registros_padme else {}

        estatus_savia = str(
            savia.get("estatus__nombre") or ""
        ).strip().upper()

        es_baja = estatus_savia == "BAJA"

        if len(registros_savia) > 1 or len(registros_padme) > 1:
            estado = "DUPLICADO"

        elif registros_savia and registros_padme:
            estado = "MATCH"

        elif registros_savia:
            estado = "BAJA SAVIA" if es_baja else "SOLO SAVIA"

        else:
            estado = "SOLO PADME"

        savia = registros_savia[0] if registros_savia else {}
        padme = registros_padme[0] if registros_padme else {}

        resultados.append({
            "eco": eco,
            "estado": estado,
            "savia_id": savia.get("id"),
            "savia_eco": savia.get("eco_unidad"),
            "padme_serial": padme.get("serial"),
            "padme_system_id": padme.get("system_id"),
            "padme_distrito": padme.get("district"),
            "padme_modelo": padme.get("model"),
            "padme_estatus": padme.get("status"),
            "padme_tipo": padme.get("type"),
            "padme_latitud": padme.get("latitude"),
            "padme_longitud": padme.get("longitude"),
            "cantidad_savia": len(registros_savia),
            "cantidad_padme": len(registros_padme),
            "savia_distrito": savia.get("activo__distrito__nombre"),
            "savia_estatus": estatus_savia,
            "es_baja_savia": es_baja,
        })

    return resultados