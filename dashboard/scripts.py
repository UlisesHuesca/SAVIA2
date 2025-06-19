from django.db.models import Q
from .models import ArticulosparaSurtir, Inventario
from requisiciones.models import Salidas  # Asegúrate de ajustar la ruta de importación según tu proyecto.
from entradas.models import EntradaArticulo, Entrada  # Asegúrate de ajustar 'mi_app.models' al nombre de tu aplicación y archivo de modelos
from compras.models import Compra
from datetime import datetime
from decimal import Decimal
import logging
from django.db.models import Sum

logger = logging.getLogger('dashboard')

def actualizar_articulos():
    folios_a_verificar = []  # Lista de folios a verificar.
    distrito_id = 2  # El ID del distrito que quieres filtrar.

    # Filtra los artículos cuyos folios sean mayores a 20000 o estén en la lista de folios a verificar, y cuyo distrito_id sea 3.
    articulos_a_actualizar = ArticulosparaSurtir.objects.filter(
        ~Q(articulos__orden__folio__in=folios_a_verificar),
        articulos__orden__folio__lte=20000,  # lte significa "less than or equal to"
        articulos__orden__distrito__id=distrito_id
    )

    # Actualiza surtir y requisitar a False para esos artículos.
    num_articulos_actualizados = articulos_a_actualizar.update(surtir=False, requisitar=False)

    print(f'Artículos actualizados: {num_articulos_actualizados}')
    return num_articulos_actualizados

# Importa tus modelos al inicio de tu archivo


def marcar_articulos_agotados(producto_id):
   
    entradas_a_actualizar = EntradaArticulo.objects.filter(
        Q(articulo_comprado__producto__producto__articulos__producto__producto__id=producto_id) &
        Q(entrada__oc__req__orden__distrito__id=5)
    )
    
    # Actualiza el campo 'agotado' a True para todos los objetos filtrados
    num_entradas_actualizadas = entradas_a_actualizar.update(agotado=True)
    
    print(f'Entradas actualizadas a agotado: {num_entradas_actualizadas}')
    return num_entradas_actualizadas

def marcar_articulos_agotados_todos():
    distrito = 2
    productos = Inventario.objects.filter(distrito_id= distrito)
    
    total_entradas_actualizadas = 0  # Inicializa el contador de entradas actualizadas
    fecha_limite = datetime(2024, 4, 15) 

    for producto in productos:
        entradas_a_actualizar = EntradaArticulo.objects.filter(
            Q(articulo_comprado__producto__producto__articulos__producto__producto__id=producto.producto_id) &
            Q(entrada__oc__req__orden__distrito__id=distrito) &
            Q(entrada__entrada_date__lt=fecha_limite) 
        )
        
        # Actualiza el campo 'agotado' a True para todos los objetos filtrados y suma al total
        num_entradas_actualizadas = entradas_a_actualizar.update(agotado=True)
        total_entradas_actualizadas += num_entradas_actualizadas  # Suma al contador total

        print(f'Entradas actualizadas a agotado para producto {producto.producto_id}: {num_entradas_actualizadas}')

    # Devuelve el total de entradas actualizadas después de procesar todos los productos
    print(f'Total de entradas actualizadas a agotado: {total_entradas_actualizadas}')
    return total_entradas_actualizadas

def marcar_articulos_agotados_vz():
    productos = Inventario.objects.filter(distrito_id=5)
    
    total_entradas_actualizadas = 0  # Inicializa el contador de entradas actualizadas
    fecha_limite = datetime(2024, 1, 5) 

    for producto in productos:
        entradas_a_actualizar = EntradaArticulo.objects.filter(
            Q(articulo_comprado__producto__producto__articulos__producto__producto__id=producto.producto_id) &
            Q(entrada__oc__req__orden__distrito__id=5) &
            Q(entrada__entrada_date__lt=fecha_limite) 
        )
        
        # Actualiza el campo 'agotado' a True para todos los objetos filtrados y suma al total
        num_entradas_actualizadas = entradas_a_actualizar.update(agotado=True)
        total_entradas_actualizadas += num_entradas_actualizadas  # Suma al contador total

        print(f'Entradas actualizadas a agotado para producto {producto.producto_id}: {num_entradas_actualizadas}')

    # Devuelve el total de entradas actualizadas después de procesar todos los productos
    print(f'Total de entradas actualizadas a agotado: {total_entradas_actualizadas}')
    return total_entradas_actualizadas

def marcar_compras_entrada_completa():
    folios_a_verificar = [2699,3755,4483,4537,5739,5941,5967,5987,5988,6043,6118,6126,6245,6395,6513,6568,6569,6674,6697,6699,6717,6725,6741,6743,6815,6832,6837,6875,6918,6919,6920,6923,6946,6951,6977,6990,6994,6997,7007,7008,7010,7012,7014,7015,7017,7021,7025,7039,7041,7042,7044,7046,7047,7048,7051,7052,7054,7056,7057,7061,7064,7065]  # Lista de folios a verificar.
    
    # Filtra las compras que no están en la lista de folios, son del distrito 3 y la entrada_completa es False.
    compras_a_actualizar = Compra.objects.filter(
        Q(folio__in = folios_a_verificar),
        req__orden__distrito__id=3,
    )
    
    # Actualiza el campo 'entrada_completa' a True para todos los objetos filtrados
    num_compras_actualizadas = compras_a_actualizar.update(entrada_completa=False)
    
    print(f'Compras actualizadas con entrada completa: {num_compras_actualizadas}')
    return num_compras_actualizadas


def marcar_compras_para_pagarse():
    folios_a_verificar = [7055,7052,7049,7047,7043,7038,7036,7029,7028,7027,7025,7024,7022,7021,7017,7016,7012,7009,7007,7006,7005,7004,7000,6999,6997,6996,6994,6993,6991,6990,6988,6987,6985,6984,6982,6981,6979,6978,6976,6974,6972,6971,6970,6969,6968,6966,6965,6964,6962,6961,6960,6958,6955,6954,6951,6949,6947,6945,6944,6943,6926,6913,6912,6911,6910,6898,6894,6880,6869,6867,6846,6828,6827,6826,6825,6808,6806,6796,6788,6786,6775,6768,6755,6708,6671,6669,6668,6627,6626,6625,6624,6621,6620,6619,6618,6616,6615,6614,6613,6612,6611,6610,6609,6608,6607,6606,6605,6604,6603,6602,6600,6599,6598,6597,6588,6543,6487,6358,6254,6155,5956,5904,5802,5610,5426,5209,5032,4740,4561,3824,2996,2806,2668,2382,2231,2202,2087,1807,1298,1267,1166,1122,818]

    # Filtra las compras que no están en la lista de folios, son del distrito 3 y la entrada_completa es False.
    compras_a_actualizar = Compra.objects.filter(
        Q(folio__in = folios_a_verificar),
        req__orden__distrito__id=3,
    )
    
    # Actualiza el campo 'entrada_completa' a True para todos los objetos filtrados
    num_compras_actualizadas = compras_a_actualizar.update(pagada=True, entrada_completa = True)
    
    print(f'Compras actualizadas con entrada completa: {num_compras_actualizadas}')
    return num_compras_actualizadas

def corregir_articulos_salida():
    """
    Recorre todas las salidas activas (no canceladas) y corrige los objetos relacionados de
    ArticulosparaSurtir si coinciden el producto y la cantidad.
    Establece salida=True, surtir=False y cantidad=0 en ArticulosparaSurtir.
    """
    total_salidas = 0
    modificados = 0
    salidas = Salidas.objects.filter(cancelada=False, complete = True)

    for salida in salidas:
        total_salidas += 1
        articulo = salida.producto
        if articulo and Decimal(salida.cantidad) == Decimal(articulo.cantidad):
            #print(f"Corrigiendo artículo:{articulo.id} {articulo.articulos.producto} con cantidad: {articulo.cantidad}| salida: {salida.id}")
            articulo.salida = True
            articulo.surtir = False
            articulo.cantidad = 0
            articulo.save(update_fields=['salida', 'surtir', 'cantidad'])
            modificados += 1
            logger.info(f"Antes: orden={articulo.articulos.orden.folio} distrito={articulo.articulos.orden.distrito} cantidad={articulo.cantidad} salida={articulo.salida} surtir={articulo.surtir}")

    logger.info(f"Evaluadas: {total_salidas} salidas completadas.")
    logger.info(f"Artículos corregidos: {modificados}")
    #print(f"Evaluadas: {total_salidas} salidas completadas.")
    #print(f"Proceso completado. Se actualizaron {modificados} artículos.")

def analizar_articulos_incompletos_distrito_1():
    fecha_inicio = datetime(2024, 6, 14)
    pendientes = []

    articulos = ArticulosparaSurtir.objects.filter(
        articulos__orden__distrito__id=1,
        created_at__date__gte=fecha_inicio,
        surtir=False,
        requisitar=False
    )

    for articulo in articulos:
        if not articulo.articulos:
            continue

        cantidad_ordenada = articulo.articulos.cantidad

        total_surtido = Salidas.objects.filter(
            producto=articulo,
            cancelada=False
        ).aggregate(total=Sum('cantidad'))['total'] or Decimal('0')

        if total_surtido < cantidad_ordenada:
            pendiente = cantidad_ordenada - total_surtido
            pendientes.append({
                'articulo_id': articulo.id,
                'orden_id': articulo.articulos.orden.id if articulo.articulos.orden else 'Sin orden',
                'cantidad_ordenada': cantidad_ordenada,
                'total_surtido': total_surtido,
                'pendiente_por_surtir': pendiente
            })

    logger.info(f"🔎 Evaluación desde 14-jun-2024 | Distrito 1")
    logger.info(f"Total artículos evaluados: {total_articulos}")
    logger.info(f"Total salidas evaluadas: {total_salidas}")
    logger.info(f"Total cantidad surtida en salidas: {total_salida_cantidad}")
    logger.info(f"Artículos con pendiente por surtir: {len(pendientes)}")

    # Imprimir resultados
    for item in pendientes:
        logger.info(
            f"Artículo ID: {item['articulo_id']} | "
            f"Orden ID: {item['orden_id']} | "
            f"Ordenado: {item['cantidad_ordenada']} | "
            f"Surtido: {item['total_surtido']} | "
            f"Pendiente: {item['pendiente_por_surtir']}"
        )

    logger.info(f"Total artículos en este estado: {len(pendientes)}")

    