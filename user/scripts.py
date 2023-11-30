from .models import BancoTB, Banco
import os
import django
from django.apps import apps

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'user.settings')
django.setup()

# Importa el modelo de origen y destino
BancoTB = apps.get_model(app_label='user', model_name='BancoTB')
Banco = apps.get_model(app_label='user', model_name='Banco')

def transferir_datos():
    for banco in BancoTB.objects.all():
        if not Banco.objects.filter(nombre =banco.BANCO).exists():
            Banco.objects.create(nombre =banco.BANCO)
            # ... y cualquier otro campo que desees transferir ...

    print("Datos transferidos con éxito.")

if __name__ == "__main__":
    transferir_datos()