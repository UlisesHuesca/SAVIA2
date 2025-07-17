from django.shortcuts import render, redirect
from user.models import Profile
from .forms import Linea_Exhibit_Form
from .models import Exhibit

from django.utils import timezone
from django.shortcuts import render
from .models import Exhibit, Linea_Exhibit
from .forms import Linea_Exhibit_Form
from user.models import Profile
from compras.models import Proveedor_direcciones

def crear_exhibit(request):
    pk_perfil = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id=pk_perfil)

    # Obtener o crear Exhibit en progreso
    exhibit, creado = Exhibit.objects.get_or_create(
        creada_por=usuario,
        hecho=False,
        defaults={
            'folio': generar_folio_unico(),
            'created_at': timezone.now()
        }
    )

    form = Linea_Exhibit_Form()

    # Procesar envío de línea nueva
    if request.method == 'POST':
        #print(request.POST)
        if 'btn_linea' in request.POST:
            form = Linea_Exhibit_Form(request.POST)
            if form.is_valid():
                linea = form.save(commit=False)
                if linea.tipo == 'Vordcab':
                    vordcab = Proveedor_direcciones.objects.get(id = 5115)
                    linea.proveedor = vordcab
                    linea.tipo_proveedor = 'PM'
                    linea.email = vordcab.email
                    linea.pagina_web = "www.grupovordcab.com"
                    #print(linea.email)
                    direccion = vordcab.domicilio
                    partes = descomponer_direccion(direccion)
                    linea.calle = partes.get('calle', '')
                    linea.colonia = partes.get('colonia', '')
                    linea.cp = partes.get('cp', '')
                    linea.municipio = partes.get('municipio', '')
                    linea.estado = vordcab.estado.nombre
                    linea.pais = vordcab.estado.pais.nombre
                    linea.telefono = vordcab.telefono
                    contacto = vordcab.contacto
                    contacto_partes = descomponer_contacto(contacto)
                    linea.contacto_nombre = contacto_partes.get('nombre', '')
                    linea.contacto_apellido = contacto_partes.get('apellido', '')
                    linea.area = "TESORERIA"
                    linea.banco = vordcab.banco
                    linea.moneda = 2
                    linea.cuenta_bancaria = vordcab.cuenta
                    linea.clabe = vordcab.clabe
                    linea.swift = vordcab.swift
                    linea.aba = "NA"
                    linea.iban = "NA"
                    linea.direccion_banco = vordcab.domicilio_banco
                    linea.observaciones_cuenta = "MONEX"
                    linea.referencia = "NA"

                linea.exhibit = exhibit
                linea.id_detalle = exhibit.lineas.count() + 1
                linea.save()
                form = Linea_Exhibit_Form()  # Limpiar formulario después de guardar
                return redirect('crear-exhibit')
            else:
                print("Formulario inválido:", form.errors)
        elif 'btn_cerrar' in request.POST:
            exhibit.hecho = True
            exhibit.save()
            return redirect('dashboard-index')  # o a donde quieras mandar al usuario
           

    lineas = exhibit.lineas.all()

    context = {
        'exhibit': exhibit,
        'form': form,
        'lineas': lineas,
    }
    return render(request, 'finanzas/crear_exhibit.html', context)

def generar_folio_unico():
    ultimo = Exhibit.objects.order_by('-folio').first()
    return (ultimo.folio + 1) if ultimo and ultimo.folio else 1

import re

def descomponer_direccion(direccion):
    resultado = {
        'calle': '',
        'colonia': '',
        'cp': '',
        'estado': ''
    }

    # Normalizamos espacios
    direccion = ' '.join(direccion.strip().split())

    # Patrón que detecta las secciones: calle → colonia → cp → municipio/estado
    patron = re.compile(
        r'(?:CALLE|AV\.?|AVENIDA)\s+(.*?)\s+(?:COL.|COLONIA|FRACCIONAMIENTO|FRACC.\.?)\s+(.*?)\s+C\.?P\.?\s+(\d{5})\s+(.*)',
        re.IGNORECASE
    )

    match = patron.search(direccion)
    if match:
        resultado['calle'] = match.group(1).strip().title()
        resultado['colonia'] = match.group(2).strip().title()
        resultado['cp'] = match.group(3).strip()
        resto = match.group(4).strip()
        if ',' in resto:
            municipio, estado = map(str.strip, resto.split(',', 1))
            resultado['municipio'] = municipio.title()
            resultado['estado'] = estado.title()
        else:
            resultado['municipio'] = resto.title()
    
    return resultado

def descomponer_contacto(contacto):
    contacto = contacto.strip().title()
    partes = contacto.split()

    if len(partes) == 2:
        return {'nombre': partes[0], 'apellido': partes[1]}
    elif len(partes) == 1:
        return {'nombre': partes[0], 'apellido': ''}
    else:
        # Si hay más de dos palabras, asumimos la primera como nombre y el resto como apellido
        return {
            'nombre': partes[0],
            'apellido': ' '.join(partes[1:])
        }