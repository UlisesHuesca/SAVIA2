from dashboard.models import ArticulosOrdenados, ArticulosparaSurtir, Order
from requisiciones.models import ArticulosRequisitados, Requis
from compras.models import Compra
from tesoreria.models import Pago

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
        pagos = Pago.objects.filter(oc = compra)
        pagado = 0
        for pago in pagos:
            # Usamos filter() en lugar de get() para manejar múltiples coincidencias
            pagado = pagado + pago.monto
            if pagado >= compra.costo_oc:
                compra.pagada
                compra.save()
               

    print('Termina ejecución')

