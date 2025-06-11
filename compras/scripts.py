from django.db.models import F, Sum, Q
from .models import ArticuloComprado, Proveedor, Compra
from requisiciones.models import Requis, ArticulosRequisitados 
from entradas.models import EntradaArticulo
from decimal import Decimal
import logging


def verificar_requisiciones_colocadas():
    print('Procesando...')
    # Obtener todas las requisiciones que cumplen con las condiciones
    requis = Requis.objects.filter(complete=True, autorizar=True, colocada=False)
    print(f"Encontradas {requis.count()} requisiciones para verificar.")
    count = 0
    for req in requis: 
        # Obtener todos los artículos comprados relacionados con la requisición que ya están completadas
        productos_requis = ArticulosRequisitados.objects.filter(req=req)
        conteo_requisitados = productos_requis.count()
        
        for producto in productos_requis:
            total = ArticuloComprado.objects.filter(producto=producto).annotate(cantidad_sumada=Sum('cantidad')).first()

            cantidad_comprada = total.cantidad_sumada if total else 0
            producto.cantidad_comprada = cantidad_comprada
            producto.save()
            if producto.cantidad_comprada == producto.cantidad:
                producto.art_surtido = True
                producto.save()  
       
        conteo_comprados = productos_requis.filter(art_surtido=True).count()
       
        
        if conteo_requisitados <= conteo_comprados:
            count = count + 1
            print(f"Requisición con ID: {req.id} ha sido marcada como colocada.{count}")
            req.colocada = True
            req.save()
           

logger = logging.getLogger('dashboard')

def corregir_entradas_articulos_comprados_y_oc():
    """
    1. Marca entrada_completa=True en ArticuloComprado cuando la suma de entradas iguala la cantidad.
    2. Luego evalúa cada Compra: si todos sus ArticuloComprado están con entrada_completa=True,
       marca Compra.entrada_completa = True
    """
    logger.info("==== INICIO del proceso de corrección de entradas y órdenes de compra ====")

    # Parte 1: Corrección por artículo comprado
    modificados_articulos = 0
    total_articulos = 0

    articulos = ArticuloComprado.objects.all()

    for articulo in articulos:
        total_articulos += 1

        suma_entradas = EntradaArticulo.objects.filter(articulo_comprado=articulo).aggregate(
            total=Sum('cantidad')
        )['total'] or Decimal('0')

        if Decimal(suma_entradas) == Decimal(articulo.cantidad) and not articulo.entrada_completa:
            articulo.entrada_completa = True
            articulo.save(update_fields=['entrada_completa'])
            logger.info(f"✅ ArtículoComprado ID={articulo.id} marcado como entrada_completa.")
            modificados_articulos += 1

    logger.info(f"Total artículos evaluados: {total_articulos}")
    logger.info(f"Artículos modificados: {modificados_articulos}")

    # Parte 2: Evaluar órdenes de compra
    compras_modificadas = 0
    total_compras = 0

    compras = Compra.objects.all()

    for oc in compras:
        total_compras += 1
        articulos_oc = oc.articulocomprado_set.all()  # related_name por defecto
        if articulos_oc.exists() and all(a.entrada_completa for a in articulos_oc):
            if not oc.entrada_completa:
                oc.entrada_completa = True
                oc.save(update_fields=['entrada_completa'])
                logger.info(f"✅ Compra ID={oc.id} marcada como entrada_completa.")
                compras_modificadas += 1

    logger.info(f"Total compras evaluadas: {total_compras}")
    logger.info(f"Compras modificadas: {compras_modificadas}")
    logger.info("==== FIN del proceso de corrección ====")

def asignar_folios_por_pais():
    
    folios_por_pais = {
        "México": 1,
        "Brasil": 1,
    }

    for pais in folios_por_pais.keys():
        proveedores = Proveedor.objects.filter(
            direcciones__estado__pais__nombre__iexact=pais
        ).exclude(
            direcciones__estatus__nombre__in=["COTIZACION", "PREALTA"]
        ).distinct().order_by('id')

        for proveedor in proveedores:
            proveedor.folio_consecutivo = folios_por_pais[pais]
            proveedor.save()
            print(f"{proveedor.razon_social} ({pais}) => Folio {folios_por_pais[pais]}")
            folios_por_pais[pais] += 1

    print("Asignación completa.")

def verificar_pago_y_marcar_pagada(folio_prueba=None):
    """
    Verifica que la suma de pagos sea mayor o igual al 95% del costo_plus_adicionales.
    Si lo es, marca la compra como pagada=True y guarda.
    Si se pasa un folio_prueba, solo verifica ese; si no, revisa todas las compras autorizadas y no pagadas.
    """
    factor_inferior = Decimal('0.95')

    compras_pendientes = Compra.objects.filter(pagada=False, autorizado2=True)

    if folio_prueba:
        compras_pendientes = compras_pendientes.filter(folio=folio_prueba)

    for compra in compras_pendientes:
        costo_total = compra.costo_plus_adicionales
        if costo_total is None:
            print(f"⚠️ Compra {compra.id} (folio {compra.folio}) no tiene costo_total definido.")
            continue

        suma_pagos = compra.pagos.aggregate(total=Sum('monto'))['total'] or Decimal('0')
        limite_inferior = costo_total * factor_inferior

        if suma_pagos >= limite_inferior:
            # Marcar como pagada
            compra.pagada = True
            compra.save()
            print(f"✅ Compra {compra.id} (folio {compra.folio}) marcada como pagada: suma de pagos {suma_pagos} >= 95% ({limite_inferior})")
        else:
            print(f"❌ Compra {compra.id} (folio {compra.folio}): suma de pagos {suma_pagos} < 95% ({limite_inferior})")