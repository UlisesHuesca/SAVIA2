from django.db.models import F, Sum, Q
from .models import ArticuloComprado
from requisiciones.models import Requis, ArticulosRequisitados 

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
           

#verificar_requisiciones_colocadas()
