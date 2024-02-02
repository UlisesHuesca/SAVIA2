import csv
from dashboard.models import Unidad, Familia, Subfamilia, Product
from django.contrib import messages

def run():
    fhand = open('template_products.csv')
    reader = csv.reader(fhand)
    next(reader) #Advance past the reader

    for row in reader:
        print(row)
        unidad = Unidad.objects.get(nombre = row[2])
        familia = Familia.objects.get(nombre = row[3])
        subfamilia = Subfamilia.objects.get(nombre = row[4], familia = familia)
        if unidad == None:
            messages.error('La unidad no existe dentro de la base de datos')
        elif familia == None:
            messages.error('La familia no existe dentro de la base de datos')
        elif subfamilia == None:
            messages.error('La subfamilia no existe dentro de la base de datos')
        else:
            producto = Product(codigo=row[0],nombre=row[1], unidad=unidad, familia=familia, subfamilia=subfamilia,especialista=row[5],servicio=row[6],baja_item=False)
            producto.save()

