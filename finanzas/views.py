from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Sum, Max
from user.models import Profile
from .forms import Linea_Exhibit_Form
from .models import Exhibit

from django.utils import timezone
from django.shortcuts import render
from .models import Exhibit, Linea_Exhibit
from .forms import Linea_Exhibit_Form
from user.models import Profile
from compras.models import Proveedor_direcciones, Moneda
import re
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, ElementTree

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
                    proveedor = Proveedor_direcciones.objects.get(id = 5115)
                    linea.area = "TESORERIA"
                    linea.pagina_web = "www.grupovordcab.com"
                    linea.observaciones_cuenta = "MONEX"
                else:
                    proveedor = linea.proveedor
                    linea.pagina_web = "NA"
                    linea.observaciones_cuenta = "NA"

                moneda = Moneda.objects.get(id=2)
                linea.proveedor = proveedor
                linea.tipo_proveedor = 'PM'
                linea.email = proveedor.email
                
                #print(linea.email)
                direccion = proveedor.domicilio
                partes = descomponer_direccion(direccion)
                linea.calle = partes.get('calle', '')
                linea.colonia = partes.get('colonia', '')
                linea.cp = partes.get('cp', '')
                linea.municipio = partes.get('municipio', '')
                linea.estado = proveedor.estado.nombre if proveedor.estado else "ND"
                linea.pais = proveedor.estado.pais.nombre if proveedor.estado else "ND"
                linea.telefono = proveedor.telefono
                contacto = proveedor.contacto
                contacto_partes = descomponer_contacto(contacto)
                linea.contacto_nombre = contacto_partes.get('nombre', '')
                linea.contacto_apellido = contacto_partes.get('apellido', '')
                linea.banco = proveedor.banco
                linea.moneda = moneda
                linea.cuenta_bancaria = proveedor.cuenta
                linea.clabe = proveedor.clabe
                linea.swift = proveedor.swift
                linea.aba = "NA"
                linea.iban = "NA"
                linea.direccion_banco = proveedor.domicilio_banco
                linea.referencia = "NA"
               

                linea.exhibit = exhibit
                linea.id_detalle = exhibit.lineas.count() + 1
                linea.save()
                form = Linea_Exhibit_Form()  # Limpiar formulario después de guardar
                return redirect('crear-exhibit')
            else:
                print("Formulario inválido:", form.errors)
        elif 'btn_crear_exhibit' in request.POST:
            ultimo_folio = Exhibit.objects.aggregate(Max('folio'))['folio__max']
            nuevo_folio = (ultimo_folio or 0) + 1

            exhibit.folio = nuevo_folio
            exhibit.hecho = True
            exhibit.save()
            return redirect('matriz-exhibit')  # o a donde quieras mandar al usuario
           

    lineas = exhibit.lineas.all()
    total_exhibit = lineas.aggregate(Sum('monto'))['monto__sum'] or 0

    context = {
        'total_exhibit':total_exhibit,
        'exhibit': exhibit,
        'form': form,
        'lineas': lineas,
    }
    return render(request, 'finanzas/crear_exhibit.html', context)

def generar_folio_unico():
    ultimo = Exhibit.objects.order_by('-folio').first()
    return (ultimo.folio + 1) if ultimo and ultimo.folio else 1


def eliminar_linea_exhibit(request, linea_id):
    if request.method == "POST":
        linea = get_object_or_404(Linea_Exhibit, id=linea_id)
        exhibit_id = linea.exhibit.id  # si necesitas volver al exhibit actual
        linea.delete()
        messages.success(request, "Línea eliminada correctamente.")
    return redirect('crear-exhibit')  # cambia por la vista actual

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
    
def matriz_exhibit(request):
    pk_perfil = request.session.get('selected_profile_id')
    usuario = Profile.objects.get(id=pk_perfil)

    exhibits = Exhibit.objects.all().order_by('-created_at')

    context = {
        'exhibits': exhibits,
        'usuario': usuario,
    }
    return render(request, 'finanzas/exhibits.html', context)

def generar_exhibit_xml(request, pk):
    exhibit = Exhibit.objects.get(pk=pk)
    root = Element('Exhibit')
    SubElement(root, 'Folio').text = str(exhibit.folio)
    SubElement(root, 'FechaCreacion').text = str(exhibit.created_at)

    lineas_element = SubElement(root, 'Lineas')

    for linea in exhibit.lineas.all():
        linea_element = SubElement(lineas_element, 'Linea')

        # Cargar proveedor
        if linea.tipo == 'Vordcab':
            proveedor = Proveedor_direcciones.objects.get(id=5115)
            linea.area = "TESORERIA"
            linea.pagina_web = "www.grupovordcab.com"
            linea.observaciones_cuenta = "MONEX"
            linea.tipo_proveedor = 'PM'
        else:
            proveedor = linea.proveedor
            linea.pagina_web = "NA"
            linea.observaciones_cuenta = "NA"
            linea.tipo_proveedor = linea.tipo_proveedor or 'PM'

        direccion = proveedor.domicilio or ''
        partes = descomponer_direccion(direccion)
        contacto_partes = descomponer_contacto(proveedor.contacto or '')

        SubElement(linea_element, 'Tipo').text = linea.tipo
        SubElement(linea_element, 'TipoProveedor').text = linea.tipo_proveedor
        SubElement(linea_element, 'RFC').text = proveedor.nombre.rfc if linea.tipo == 'Vordcab' else (proveedor.nombre.rfc if proveedor.nombre else 'ND')
        SubElement(linea_element, 'Email').text = proveedor.email or ''
        SubElement(linea_element, 'Calle').text = partes.get('calle', '')
        SubElement(linea_element, 'Colonia').text = partes.get('colonia', '')
        SubElement(linea_element, 'CP').text = partes.get('cp', '')
        SubElement(linea_element, 'Municipio').text = partes.get('municipio', '')
        SubElement(linea_element, 'Estado').text = proveedor.estado.nombre if proveedor.estado else 'ND'
        SubElement(linea_element, 'Pais').text = proveedor.estado.pais.nombre if proveedor.estado and proveedor.estado.pais else 'ND'
        SubElement(linea_element, 'Telefono').text = proveedor.telefono or ''
        SubElement(linea_element, 'ContactoNombre').text = contacto_partes.get('nombre', '')
        SubElement(linea_element, 'ContactoApellido').text = contacto_partes.get('apellido', '')
        SubElement(linea_element, 'Solicitud').text = linea.solicitud or ''
        SubElement(linea_element, 'Descripcion').text = linea.descripcion or ''
        SubElement(linea_element, 'Observaciones').text = linea.observaciones or ''
        SubElement(linea_element, 'Monto').text = str(linea.monto or '0.00')
        SubElement(linea_element, 'Cuenta').text = proveedor.cuenta or ''
        SubElement(linea_element, 'CLABE').text = proveedor.clabe or ''
        SubElement(linea_element, 'SWIFT').text = proveedor.swift or ''
        SubElement(linea_element, 'ABA').text = linea.aba or 'NA'
        SubElement(linea_element, 'IBAN').text = linea.iban or 'NA'
        SubElement(linea_element, 'DireccionBanco').text = proveedor.domicilio_banco or ''
        SubElement(linea_element, 'ObservacionesCuenta').text = linea.observaciones_cuenta or ''
        SubElement(linea_element, 'Referencia').text = linea.referencia or ''
        SubElement(linea_element, 'Area').text = linea.area or ''
        SubElement(linea_element, 'PaginaWeb').text = linea.pagina_web or ''

    tree = ElementTree(root)
    response = HttpResponse(content_type='application/xml')
    response['Content-Disposition'] = f'attachment; filename="exhibit_{exhibit.folio}.xml"'
    tree.write(response, encoding='utf-8', xml_declaration=True)
    return response

def ver_pagos_relacionados(request, exhibit_id):
    # Usamos get_object_or_404 para obtener el exhibit.
    # Si no existe, mostrará una página de error 404 automáticamente.
    exhibit = get_object_or_404(Exhibit, pk=exhibit_id)

    # Gracias al related_name='pagos' en tu modelo Pago,
    # puedes acceder a todos los pagos relacionados de esta forma.
    pagos_relacionados = exhibit.pagos.all()

    context = {
        'exhibit': exhibit,
        'pagos': pagos_relacionados,
    }

    # Renderizamos un nuevo template que crearemos en el siguiente paso
    return render(request, 'finanzas/pagos_por_exhibit.html', context)