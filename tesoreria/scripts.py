from compras.models import Compra
from tesoreria.models import Pago
from django.db.models import F, Sum, Q


def verificar_compras_colocadas():
    print('Procesando...')
    # Obtener todas las compras que cumplen con las condiciones
    compras = Compra.objects.filter(autorizado2=True, pagada=False)
    print(f"Encontradas {compras.count()} compras para verificar.")
    
    count = 0
    for compra in compras:
        # Obtener la suma de los montos de los pagos relacionados con la compra
        total = Pago.objects.filter(oc=compra).aggregate(cantidad_sumada=Sum('monto'))
        
        monto_total = total['cantidad_sumada'] if total['cantidad_sumada'] is not None else 0
        
        if monto_total >= compra.costo_oc:  # Asumiendo que "monto" es el campo de la Compra con el monto total
            count += 1
            print(f"Compra con ID: {compra.id} ha sido marcada como pagada. {count}")
            compra.pagada = True
            compra.save()

#verificar_compras_colocadas()
