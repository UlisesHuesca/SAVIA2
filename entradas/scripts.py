from django.db.models import Sum, Q
from compras.models import Compra, ArticuloComprado
from entradas.models import EntradaArticulo 
from dashboard.models import Order  

def verificar_compras_entregadas():
    print('Procesando...')
    
    # Obtiene las compras que cumplan con ciertas condiciones.
    compras = Compra.objects.filter(
        Q(cond_de_pago__nombre='CREDITO') | Q(pagada=True),
        solo_servicios=False,
        entrada_completa=False,
        autorizado2=True
    ).order_by('-folio')
    
    print(f"Encontradas {compras.count()} compras para verificar.")
    
    count = 0
    
    # Itera sobre cada compra para verificar los artículos asociados.
    for compra in compras:
        # Obtiene los artículos comprados relacionados con la compra.
        productos_compras = ArticuloComprado.objects.filter(oc=compra)
        conteo_comprados = productos_compras.count()

        # Verifica y actualiza la cantidad entregada para cada artículo comprado.
        for producto in productos_compras:
            total = EntradaArticulo.objects.filter(articulo_comprado=producto).annotate(cantidad_sumada=Sum('cantidad')).first()
            cantidad_entregada = total.cantidad_sumada if total else 0
            
            producto.cantidad_pendiente = producto.cantidad - cantidad_entregada
            producto.save()

            # Marca el producto como entrada completa si no queda cantidad pendiente.
            if producto.cantidad_pendiente == 0:
                producto.entrada_completa = True
                producto.save()

        # Conteo de productos con entrada completa.
        conteo_entregados = productos_compras.filter(entrada_completa=True).count()

        # Si todos los productos de la compra están completos, marca la compra como entregada.
        if conteo_comprados <= conteo_entregados:
            count += 1
            print(f"Compra con ID: {compra.id} ha sido marcada como entregada. Total entregadas: {count}")
            compra.entrada_completa = True
            compra.save()

    print("Script finalizado.")

def update_compras_solo_servicios():
    compras = Compra.objects.filter(Q(cond_de_pago__nombre='CREDITO') | Q(pagada=True), solo_servicios=False, entrada_completa=False, autorizado2=True).order_by('-folio')
    
    for compra in compras:
        articulos_entrada = ArticuloComprado.objects.filter(oc=compra, entrada_completa=False)
        servicios_pendientes = articulos_entrada.filter(producto__producto__articulos__producto__producto__servicio=True)
        cant_entradas = articulos_entrada.count()
        cant_servicios = servicios_pendientes.count()

        if cant_entradas == cant_servicios and cant_entradas > 0:
            compra.solo_servicios = True
            compra.save()


    print("Script finalizado.")

def verificar_compras_entregadas_iter2():
    print('Procesando...')
    
    compras = Compra.objects.filter(
        Q(cond_de_pago__nombre='CREDITO') | Q(pagada=True),
        solo_servicios=False,
        entrada_completa=False,
        autorizado2=True
    ).order_by('-folio')
    
    print(f"Encontradas {compras.count()} compras para verificar.")
    
    count = 0
    
    for compra in compras:
        productos_compras = ArticuloComprado.objects.filter(oc=compra)
        conteo_comprados = productos_compras.count()
        todos_los_productos_completos = True  # Nueva variable

        for producto in productos_compras:
            total = EntradaArticulo.objects.filter(articulo_comprado=producto).annotate(cantidad_sumada=Sum('cantidad')).first()
            cantidad_entregada = total.cantidad_sumada if total else 0
            producto.cantidad_pendiente = producto.cantidad - cantidad_entregada
            producto.save()

            if producto.cantidad_pendiente != 0:
                producto.entrada_completa = False
                producto.save()
                todos_los_productos_completos = False  # Actualiza la variable si un producto no está completo

        if todos_los_productos_completos:
            compra.entrada_completa = True
            count += 1
            print(f"Compra con ID: {compra.id} ha sido marcada como entregada. Total entregadas: {count}")
        else:
            compra.entrada_completa = False
            print(f"Compra con ID: {compra.id} no está completamente entregada.")

        compra.save()

    print("Script finalizado.")

def actualizar_status_resurtimiento():
#Este script está con la idea de actualizar las migraciones 

    entrada_res = EntradaArticulo.objects.filter(
        articulo_comprado__producto__producto__articulos__orden__tipo__tipo='resurtimiento',
        agotado=False
    )

    # Actualizar el campo 'agotado' de los objetos filtrados.
    for entrada in entrada_res:
        entrada.agotado=True
        entrada.save()