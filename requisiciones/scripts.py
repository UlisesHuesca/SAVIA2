from dashboard.models import ArticulosOrdenados, ArticulosparaSurtir, Order
from requisiciones.models import ArticulosRequisitados, Requis
from compras.models import Compra
from tesoreria.models import Pago
from django.db.models import Q

def Actualizar_solicitudes():
    print('Empieza ejecución')
    ordenes = Order.objects.all()
    articulos_ordenados = ArticulosOrdenados.objects.all()

    for articulo_ordenado in articulos_ordenados:
        articulos_surtir = ArticulosparaSurtir.objects.filter(articulos=articulo_ordenado)

        for articulo_surtido in articulos_surtir:
            # Usamos filter() en lugar de get() para manejar múltiples coincidencias
            articulos_requisitados = ArticulosRequisitados.objects.filter(producto=articulo_surtido)


            if articulos_requisitados.exists():
                # Si existe al menos un ArticulosRequisitados correspondiente
                for articulo in articulos_requisitados:
                    orden = ordenes.get(id = articulo.producto.articulos.orden.id)
                    orden.requisitar = 0
                    orden.requisitado = 1
                    orden.save()

    print('Termina ejecución')

def Actualizar_ocs_pagadas():
    print('Empieza ejecución')
    compras = Compra.objects.all()
    #articulos_ordenados = ArticulosComprados.objects.all()
   
    for compra in compras:
        pagos = Pago.objects.filter(oc = compra, oc__req__orden__distrito__id=3,)
        pagado = 0
        for pago in pagos:
            # Usamos filter() en lugar de get() para manejar múltiples coincidencias
            pagado = pagado + pago.monto
            if pagado >= compra.costo_oc:
                compra.pagada
                compra.save()
                print(f'OC Actualizada: {compra.id}')  # Imprime el ID de la OC actualizada
               

    print('Termina ejecución')


def actualizar_solicitudes():
    folios_a_verificar = [8849, 15215, 15719, 19173, 19782]  # Los folios que quieres verificar.
    distrito_id = 3  # El ID del distrito específico.

    # Filtra las requisiciones cuyo orden no está en la lista y pertenecen al distrito_id 3.
    solicitudes_a_actualizar = Order.objects.filter(
        ~Q(folio__in=folios_a_verificar),
        distrito__id=distrito_id
    )

    # Actualiza 'requisitar' a False para esas requisiciones.
    num_solicitudes_actualizadas = solicitudes_a_actualizar.update(requisitar=False)

    print(f'Requisiciones actualizadas: {num_solicitudes_actualizadas}')
    return num_solicitudes_actualizadas
