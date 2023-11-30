import os
import django
from django.apps import apps

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard.settings')
django.setup()

# Importa el modelo de origen y destino
UnidadTB = apps.get_model(app_label='dashboard', model_name='UnidadTB')
Unidad = apps.get_model(app_label='dashboard', model_name='Unidad')

def transferir_datos():
    for unidad in UnidadTB.objects.all():
        if not Unidad.objects.filter(nombre=unidad.NOMBRE).exists():  # Asume que ambos modelos tienen un campo llamado 'nombre_unidad'
            Unidad.objects.create(nombre=unidad.NOMBRE)
            # ... y cualquier otro campo que desees transferir ...

    print("Datos transferidos con éxito.")

if __name__ == "__main__":
    transferir_datos()
