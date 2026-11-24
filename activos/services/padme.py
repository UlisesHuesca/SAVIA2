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

def normalizar_eco_motor(valor):

    if valor is None:
        return ""

    eco = unicodedata.normalize("NFKC", str(valor))
    eco = eco.strip().upper()

    # Unificar variantes de guiones
    eco = re.sub(r"[‐-‒–—−]", "-", eco)

    # Eliminar espacios
    eco = re.sub(r"\s+", "", eco)

    # Eliminar prefijos conocidos de distrito
    prefijos = ["VHSA", "PZR", "ALT", "VDT", "VZR"]

    patron = rf"^(?:{'|'.join(prefijos)})[.\-_]*(?=M-*\d+$)"

    eco = re.sub(patron, "", eco)

    # Corregir guiones consecutivos
    eco = re.sub(r"-+", "-", eco)

    # Validar que sea un económico de motor
    match = re.fullmatch(r"M-?(\d+)", eco)

    if match:
        return f"M-{int(match.group(1)):03d}"

    # No corresponde a un económico de motor
    return ""


# =========================================================
# 3. CONFIGURACIÓN DE ENDPOINTS PADME
# =========================================================

CONFIGURACION_PADME = {
    "UBM": {
        "categoria_savia": "UBM",
        "url": settings.PADME_API_URL,
        "campo_savia": "eco_unidad",
        "normalizador": normalizar_eco,

        "campos": {
            "serial": "serial",
            "system_id": "system_id",
            "distrito": "district",
            "modelo": "model",
            "estatus": "status",
            "tipo": "type",
            "latitud": "latitude",
            "longitud": "longitude",
        },
    },

    "MOTOR": {
        "categoria_savia": "MOTOR",
        "url": settings.PADME_API_MOTORES_URL,
        "campo_savia": "eco_unidad",
        "normalizador": normalizar_eco_motor,

        "campos": {
            "serial": "ice_serial",
            "system_id": "ice_system_id",
            "distrito": "ice_district",
            "modelo": "ice_model",
            "marca": "ice_brand",
        },
    },
}



def conciliar_activos_padme(categoria="UBM"):

    categoria = categoria.strip().upper()

    configuracion = CONFIGURACION_PADME.get(categoria)

    if configuracion is None:
        raise ValueError(
            f"Categoría no soportada: {categoria}"
        )

    categoria_savia = configuracion["categoria_savia"]
    campo_savia = configuracion["campo_savia"]
    normalizador = configuracion["normalizador"]
    campos_padme = configuracion["campos"]

    # =====================================================
    # 1. CONSULTAR API PADME
    # =====================================================

    response = requests.get(
        configuracion["url"],
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

    # =====================================================
    # 2. CONSULTAR ACTIVOS SAVIA
    # =====================================================

    activos_savia = Activo.objects.filter(
        categoria__nombre=categoria_savia
    ).exclude(
        **{f"{campo_savia}__isnull": True}
    ).exclude(
        **{campo_savia: ""}
    ).values(
        "id",
        "eco_unidad",
        campo_savia,
        "activo__distrito__nombre",
        "estatus__nombre",
    ).order_by("id")

    # =====================================================
    # 3. AGRUPAR REGISTROS
    # =====================================================

    savia_por_eco = defaultdict(list)
    padme_por_eco = defaultdict(list)

    for activo in activos_savia:

        eco = normalizador(activo.get(campo_savia))

        if eco:
            savia_por_eco[eco].append(activo)

    for activo in datos_padme:

        eco = normalizador(
            activo.get(campos_padme["serial"])
        )

        if eco:
            padme_por_eco[eco].append(activo)

    # =====================================================
    # 4. CONCILIAR REGISTROS
    # =====================================================

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

        # -------------------------------------------------
        # Clasificación
        # -------------------------------------------------

        if len(registros_savia) > 1 or len(registros_padme) > 1:

            estado = "DUPLICADO"

        elif registros_savia and registros_padme:

            estado = "MATCH"

        elif registros_savia:

            estado = "BAJA SAVIA" if es_baja else "SOLO SAVIA"

        else:

            estado = "SOLO PADME"

        # -------------------------------------------------
        # Obtener campos según el endpoint
        # -------------------------------------------------

        def obtener_padme(campo):

            nombre_campo = campos_padme.get(campo)

            if nombre_campo is None:
                return None

            return padme.get(nombre_campo)

        # -------------------------------------------------
        # Construcción del resultado
        # -------------------------------------------------

        resultados.append({

            "categoria": categoria,

            "eco": eco,
            "estado": estado,

            # SAVIA
            "savia_id": savia.get("id"),
            "savia_eco": savia.get("eco_unidad"),
            "savia_identificador": savia.get(campo_savia),

            "savia_distrito": savia.get(
                "activo__distrito__nombre"
            ),

            "savia_estatus": estatus_savia,
            "es_baja_savia": es_baja,

            # PADME
            "padme_serial": obtener_padme("serial"),
            "padme_system_id": obtener_padme("system_id"),
            "padme_distrito": obtener_padme("distrito"),
            "padme_modelo": obtener_padme("modelo"),
            "padme_marca": obtener_padme("marca"),
            "padme_estatus": obtener_padme("estatus"),
            "padme_tipo": obtener_padme("tipo"),
            "padme_latitud": obtener_padme("latitud"),
            "padme_longitud": obtener_padme("longitud"),

            # Duplicados
            "cantidad_savia": len(registros_savia),
            "cantidad_padme": len(registros_padme),
        })

    return resultados