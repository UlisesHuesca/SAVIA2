from dashboard.models import Order
from requisiciones.models import Requis
#from django.db.models import F, Sum, Q

def verificar_solicitudes():
    print('Procesando...')
    # Obtener todas las órdenes que cumplen con las condiciones
    ordenes = Order.objects.filter(complete=True)
    print(f"Encontradas {ordenes.count()} órdenes para verificar.")

    count = 0
    for orden in ordenes:
        try:
            # Intentar obtener un objeto Requis asociado a la orden
            requis = Requis.objects.filter(orden=orden)
            orden.requisitado = True
            orden.requisitar = False
        except Requis.DoesNotExist:
            # Si no existe un objeto Requis asociado, marcar como False
            orden.requisitado = False
        
        orden.save()  # Guardar los cambios en la base de datos
        count += 1

    print(f"{count} órdenes han sido actualizadas.")

           

#verificar_requisiciones_colocadas()