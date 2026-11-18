
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

from dashboard.models import (
    Product,
    ProductoTerminado,
    ComponenteProductoTerminado,
)


def explosion_bom(producto_terminado, cantidad=Decimal("1")):
    """
    Calcula la explosión multinivel de materiales de un
    ProductoTerminado.

    Funcionalidades:
    - Recorre recursivamente equipos, subcomponentes y piezas.
    - Multiplica cantidades según cada nivel de fabricación.
    - Consolida materiales repetidos por Product.id.
    - Agrupa materiales consolidados por familia.
    - Calcula subcomponentes requeridos.
    - Detecta referencias circulares.
    - Respeta la base de datos del producto recibido.

    No modifica inventarios, solicitudes ni unidades fabricadas.
    """

    # ========================================================
    # 1. VALIDAR CANTIDAD
    # ========================================================

    try:
        cantidad = Decimal(str(cantidad))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError(
            "La cantidad a fabricar debe ser un número válido."
        )

    if not cantidad.is_finite() or cantidad <= 0:
        raise ValidationError(
            "La cantidad a fabricar debe ser mayor que cero."
        )

    if not isinstance(producto_terminado, ProductoTerminado):
        raise ValidationError(
            "Se requiere una instancia de ProductoTerminado."
        )

    if producto_terminado.pk is None:
        raise ValidationError(
            "El producto terminado debe estar guardado."
        )

    database = producto_terminado._state.db or "default"

    # ========================================================
    # 2. ESTRUCTURAS DE ACUMULACIÓN
    # ========================================================

    # Evita repetir consultas para productos utilizados
    # en distintas ramas de una misma BOM.
    cache_componentes = {}

    # Cantidad total requerida por material (Product.id).
    materiales = defaultdict(lambda: Decimal("0"))

    # Cantidad total requerida por producto fabricable.
    subcomponentes = defaultdict(lambda: Decimal("0"))

    # ========================================================
    # 3. CONSULTAR COMPONENTES DE CADA PRODUCTO
    # ========================================================

    def obtener_componentes(producto_id):

        if producto_id not in cache_componentes:

            cache_componentes[producto_id] = list(
                ComponenteProductoTerminado.objects.using(database)
                .filter(producto_padre_id=producto_id)
                .select_related(
                    "material",
                    "producto_hijo__producto",
                )
                .order_by("pk")
            )

        return cache_componentes[producto_id]

    # ========================================================
    # 4. RECORRIDO RECURSIVO DE LA BOM
    # ========================================================

    def recorrer(producto_id, multiplicador, ruta):

        # Detectar ciclos en la rama actual.
        if producto_id in ruta:
            raise ValidationError(
                "Se detectó una referencia circular en la BOM. "
                f"ProductoTerminado ID: {producto_id}"
            )

        ruta_actual = ruta | {producto_id}

        for componente in obtener_componentes(producto_id):

            # Validar cantidad del renglón.
            cantidad_componente = componente.cantidad

            if (
                cantidad_componente is None
                or not cantidad_componente.is_finite()
                or cantidad_componente <= 0
            ):
                raise ValidationError(
                    f"Cantidad inválida en el renglón BOM "
                    f"ID {componente.pk}."
                )

            cantidad_requerida = (
                multiplicador * cantidad_componente
            )

            tiene_material = componente.material_id is not None
            tiene_hijo = componente.producto_hijo_id is not None

            # Exactamente una de las dos relaciones debe existir.
            if tiene_material == tiene_hijo:
                raise ValidationError(
                    f"El renglón BOM {componente.pk} debe tener "
                    "un material o un producto fabricable, "
                    "pero no ambos."
                )

            # ------------------------------------------------
            # MATERIAL DIRECTO
            # ------------------------------------------------

            if tiene_material:

                materiales[componente.material_id] += (
                    cantidad_requerida
                )

            # ------------------------------------------------
            # SUBCOMPONENTE O PIEZA FABRICABLE
            # ------------------------------------------------

            else:

                hijo_id = componente.producto_hijo_id

                subcomponentes[hijo_id] += cantidad_requerida

                recorrer(
                    producto_id=hijo_id,
                    multiplicador=cantidad_requerida,
                    ruta=ruta_actual,
                )

    # Ejecutar la explosión.
    recorrer(
        producto_id=producto_terminado.pk,
        multiplicador=cantidad,
        ruta=set(),
    )

    # ========================================================
    # 5. RECUPERAR MATERIALES CONSOLIDADOS
    # ========================================================

    productos = (
        Product.objects.using(database)
        .filter(pk__in=materiales.keys())
        .select_related("unidad", "familia")
    )

    resultado_materiales = []

    for producto in productos:

        resultado_materiales.append({
            "producto": producto,
            "cantidad": materiales[producto.pk],
        })

    # Ordenar por código.
    resultado_materiales.sort(
        key=lambda item: (
            item["producto"].codigo or "",
            item["producto"].pk,
        )
    )

    # ========================================================
    # 6. AGRUPAR MATERIALES POR FAMILIA
    # ========================================================

    familias_agrupadas = {}

    for item in resultado_materiales:

        producto = item["producto"]

        familia_id = producto.familia_id

        familia_nombre = (
            str(producto.familia)
            if familia_id is not None
            else "SIN FAMILIA"
        )

        if familia_id not in familias_agrupadas:

            familias_agrupadas[familia_id] = {
                "id": familia_id,
                "nombre": familia_nombre,
                "materiales": [],
                "total_materiales": 0,
            }

        familias_agrupadas[familia_id]["materiales"].append(
            item
        )

        familias_agrupadas[familia_id]["total_materiales"] += 1

    # Familias en orden alfabético, SIN FAMILIA al final.
    resultado_familias = sorted(
        familias_agrupadas.values(),
        key=lambda grupo: (
            grupo["id"] is None,
            grupo["nombre"].casefold(),
        )
    )

    # ========================================================
    # 7. RECUPERAR SUBCOMPONENTES CONSOLIDADOS
    # ========================================================

    productos_fabricables = (
        ProductoTerminado.objects.using(database)
        .filter(pk__in=subcomponentes.keys())
        .select_related("producto")
    )

    resultado_subcomponentes = []

    for producto in productos_fabricables:

        resultado_subcomponentes.append({
            "producto": producto,
            "cantidad": subcomponentes[producto.pk],
        })

    resultado_subcomponentes.sort(
        key=lambda item: (
            item["producto"].producto.codigo or "",
            item["producto"].pk,
        )
    )

    # ========================================================
    # 8. DEVOLVER RESULTADOS
    # ========================================================

    return {
        "producto": producto_terminado,
        "cantidad": cantidad,

        # Lista plana de materiales consolidados.
        "materiales": resultado_materiales,

        # Lista agrupada por familia para la tabla dinámica.
        "familias": resultado_familias,

        # Productos fabricables requeridos.
        "subcomponentes": resultado_subcomponentes,

        # Indicadores.
        "total_materiales": len(resultado_materiales),
        "total_familias": len(resultado_familias),
        "total_subcomponentes": len(resultado_subcomponentes),
    }
