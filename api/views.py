from django.shortcuts import render,  redirect
from django.http import FileResponse, JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from dashboard.models import Inventario, Order, Product, ArticulosOrdenados, ArticulosparaSurtir
from compras.models import Compra, Proveedor_direcciones, Moneda, Proveedor, ArticuloComprado
from solicitudes.models import Proyecto, Subproyecto, 
from requisiciones.models import Requis, ArticulosRequisitados
from user.models import Profile, Distrito
from .serializers import InventarioSerializer, CompraSerializer, ProveedorDireccionesSerializer, ProyectoSerializer, SubProyectoSerializer, MonedaSerializer
from .serializers import ProfileSerializer, DistritoSerializer, RequisicionSerializer, ProveedorSerializer, OrdenSerializer, Articulos_Ordenados_Serializer
from .serializers import Articulos_para_Surtir_Serializer, Articulos_Requisitados_Serializer, Articulo_Comprado_Serializer, ProductSerializer

import requests
from django.contrib.auth.models import User
from user.models import CustomUser, Empresa
from django.contrib.auth.decorators import login_required
from rest_framework.views import APIView


from compras.views import generar_pdf
from rest_framework import status
from user.decorators import perfil_seleccionado_required
from api.models import TablaFestivos
from datetime import datetime
from django.contrib import messages
import logging
from django.utils import timezone
logger = logging.getLogger("user.middleware")

#import openai

from openai import OpenAI
#import os
from django.conf import settings
import mysql.connector
client = OpenAI(
    organization='org-9Legd0seRBYosepjlvTnzipq',
    project='proj_82cTfrUnAMXikaj5cdr1Dk5a',
    api_key = settings.OPENAI_API_KEY,
    )


# Create your views here.
@api_view(['GET'])
@authentication_classes([SessionAuthentication,TokenAuthentication])
@permission_classes([IsAuthenticated])
def monedas_api(request):
    monedas = Moneda.objects.all()
    #page = request.query_params.get('page', 1)
    #per_page = request.query_params.get('per_page', 20)
    #
    #ordering = request.query_params.get('ordering')

    #if ordering:
    #    monedas = monedas.order_by(ordering)
        
    
    serialized_monedas = MonedaSerializer(monedas, many=True)

    #paginator = Paginator(monedas, per_page=per_page)
    #try: 
    #    monedas = paginator.page(number=page)
    #except EmptyPage:
    #    monedas = []
        
    return Response(serialized_monedas.data)

# Create your views here.
@api_view(['GET'])
@authentication_classes([SessionAuthentication,TokenAuthentication])
@permission_classes([IsAuthenticated])
def profiles_api(request):
    profiles = Profile.objects.all()
        
    serialized_profiles = ProfileSerializer(profiles, many=True)
        
    return Response(serialized_profiles.data)

# Create your views here.
@api_view(['GET'])
@authentication_classes([SessionAuthentication,TokenAuthentication])
@permission_classes([IsAuthenticated])
def proyectos_api(request):
    proyectos = Proyecto.objects.filter(activo = True)
    #page = request.query_params.get('page', 1)
    #per_page = request.query_params.get('per_page', 20)
    #
    #ordering = request.query_params.get('ordering')

    #if ordering:
    #    proyectos = Proyecto.order_by(ordering)
        
    
    serialized_proyectos = ProyectoSerializer(proyectos, many=True)

    #paginator = Paginator(proyectos, per_page=per_page)
    #try: 
    #    proyectos = paginator.page(number=page)
    #except EmptyPage:
    #    proyectos = []
        
    return Response(serialized_proyectos.data)

@api_view(['GET'])
@authentication_classes([SessionAuthentication,TokenAuthentication])
@permission_classes([IsAuthenticated])
def subproyectos_api(request):
    subproyectos = Subproyecto.objects.filter(activo = True)
    #page = request.query_params.get('page', 1)
    #per_page = request.query_params.get('per_page', 20)
    #
    #ordering = request.query_params.get('ordering')

    #if ordering:
    #    subproyectos = Subproyecto.order_by(ordering)
        
    
    serialized_subproyectos = SubProyectoSerializer(subproyectos, many=True)

    #paginator = Paginator(subproyectos, per_page=per_page)
    #try: 
    #    subproyectos = paginator.page(number=page)
    #except EmptyPage:
    #    subproyectos = []
        
    return Response(serialized_subproyectos.data)


#@api_view(['GET'])
#@authentication_classes([TokenAuthentication])
#@permission_classes([IsAuthenticated])
#def productos_api(request):
#    productos = Product.objects.all()
#    serializer = ProductSerializer(productos, many=True)
#    return Response(serializer.data)


#@api_view(['GET'])
#@authentication_classes([TokenAuthentication])
#@permission_classes([IsAuthenticated])
#def inventario_api(request):
#    inventario = Inventario.objects.all()
#    serializer = InventarioSerializer(inventario, many=True)
#    return Response(serializer.data)

@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def solicitudes_api(request):
    solicitudes = Order.objects.filter(complete=True).order_by("id")
    serializer = OrdenSerializer(solicitudes, many=True)
    return Response(serializer.data)

#@api_view(["GET"])
#@authentication_classes([TokenAuthentication])
#@permission_classes([IsAuthenticated])
#def productos_solicitados_api(request):
#    articulos = ArticulosOrdenados.objects.all().order_by("id")
#    serializer = Articulos_Ordenados_Serializer(articulos, many=True)
#    return Response(serializer.data)

@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def productos_surtir_api(request):
    productos_surtir = ArticulosparaSurtir.objects.all().order_by("id")
    serializer = Articulos_para_Surtir_Serializer(productos_surtir, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def requisiciones_api(request):
    requisiciones = Requis.objects.filter(complete=True).order_by("id")
    serializer = RequisicionSerializer(requisiciones, many=True)
    return Response(serializer.data)

@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def productos_requisitados_api(request):
    productos_requisitados = ArticulosRequisitados.objects.all().order_by("id")
    serializer = Articulos_Requisitados_Serializer(productos_requisitados, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def CompraAPI(request):


    compras = Compra.objects.filter(complete = True)

    serialized_compras = CompraSerializer(compras, many=True)
        
    return Response(serialized_compras.data)

@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def productos_comprados_api(request):
    productos_comprados = ArticuloComprado.objects.all().order_by("id")
    serializer = Articulo_Comprado_Serializer(productos_comprados, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([SessionAuthentication,TokenAuthentication])
@permission_classes([IsAuthenticated])
def proveedor_direccion_api(request):
    #registra el acceso a la api
    #print(f"Usuario autenticado: {request.user}")
    #user = request.user
    #ip_address = request.META.get('REMOTE_ADDR')
    #logger.info(f"GET {request.path} by {user.first_name} {user.last_name} from {ip_address}")
    
    proveedores = Proveedor_direcciones.objects.filter(completo = True)
    #page = request.query_params.get('page', 1)
    #per_page = request.query_params.get('per_page', 20)
    #
    #ordering = request.query_params.get('ordering')

    #if ordering:
    #    proveedores = Proveedor_direcciones.order_by(ordering)
        
    #paginator = Paginator(proveedores, per_page=per_page)
    #try: 
    #    proveedores = paginator.page(number=page)
    #except EmptyPage:
    #    proveedores = []
    serialized_proveedores = ProveedorDireccionesSerializer(proveedores, many=True)
        
    return Response(serialized_proveedores.data)

@api_view(['GET'])
@authentication_classes([SessionAuthentication,TokenAuthentication])
@permission_classes([IsAuthenticated])
def proveedor_api(request):
    #registra el acceso a la api
    #print(f"Usuario autenticado: {request.user}")
    #user = request.user
    #ip_address = request.META.get('REMOTE_ADDR')
    #logger.info(f"GET {request.path} by {user.first_name} {user.last_name} from {ip_address}")
    
    proveedores = Proveedor.objects.filter(completo = True)
    #page = request.query_params.get('page', 1)
    #per_page = request.query_params.get('per_page', 20)
    #
    #ordering = request.query_params.get('ordering')

    #if ordering:
    #    proveedores = Proveedor.order_by(ordering)
        
    #paginator = Paginator(proveedores, per_page=per_page)
    #try: 
    #    proveedores = paginator.page(number=page)
    #except EmptyPage:
    #    proveedores = []
    serialized_proveedores = ProveedorSerializer(proveedores, many=True)
        
    return Response(serialized_proveedores.data)

@api_view(['GET'])
@authentication_classes([SessionAuthentication,TokenAuthentication])
@permission_classes([IsAuthenticated])
def distritos_api(request):
    #registra el acceso a la api
    #print(f"Usuario autenticado: {request.user}")
    #user = request.user
    #ip_address = request.META.get('REMOTE_ADDR')
    #logger.info(f"GET {request.path} by {user.first_name} {user.last_name} from {ip_address}")
    
    distritos = Distrito.objects.filter(status = True)
    #page = request.query_params.get('page', 1)
    #per_page = request.query_params.get('per_page', 20)
    #
    #ordering = request.query_params.get('ordering')

    #if ordering:
    #    distritos = Distrito.order_by(ordering)
        
    #paginator = Paginator(distritos, per_page=per_page)
    #try: 
    #    distritos = paginator.page(number=page)
    #except EmptyPage:
    #    distritos = []
    serialized_distritos = DistritoSerializer(distritos, many=True)
        
    return Response(serialized_distritos.data)



#url = 'https://vordcab.cloud/apiapp/perfiles/'
#token = 'defa1b040b2e8acf4d9ab20127e87d820eb913b9'
@perfil_seleccionado_required
def obtener_perfiles(request):
    actualizado = False
    empleados_actualizados = []  # Lista para almacenar los usuarios actualizados

    if request.method == 'POST':
        actualizado = True  # Actualizar mensaje en template
        #url = 'http://127.0.0.1:9000/apiapp/perfiles/'
        #token = 'f36cf2df116c3aeab68b9ee948331f382f5edcc0'
        url = 'https://vordcab.cloud/apiapp/perfiles/'
        token = 'defa1b040b2e8acf4d9ab20127e87d820eb913b9'
        headers = {
            'Authorization': f'Token {token}'
        }

        # Hacer la solicitud a la API con los encabezados
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # Procesar el JSON de la respuesta
            data = response.json()

            # Iterar sobre cada perfil recibido en el JSON
            for perfil in data:
                correo_vordcab = perfil.get('correo_vordcab')
                baja = perfil.get('baja', False)  # Por defecto, es False si no existe
                nivel_data = perfil.get('nivel')  # Obtener datos del nivel
                empresa = perfil.get('empresa', {}).get('empresa')

                if empresa == 'VORDCAB':
                    empresa = 'Grupo Vordcab S.A. de C.V.'

                # Extraer el nivel del JSON, si existe
                nivel = nivel_data['nivel']['nivel'] if nivel_data and nivel_data.get('nivel') else None

                try:
                    # Buscar al usuario por su correo electrónico
                    usuario = User.objects.get(email=correo_vordcab)
                    custom_user = CustomUser.objects.get(staff=usuario)  # Obtener el CustomUser relacionado

                    # Determinar si se necesita una actualización
                    estado_anterior = usuario.is_active
                    nivel_anterior = custom_user.nivel
                    empresa_anterior = custom_user.empresa.nombre if custom_user.empresa else None

                    cambio = False  # variable que indica si hubo un cambio

                    # Actualizar el estado si ha cambiado
                    if baja:
                        if usuario.is_active:
                            usuario.is_active = False
                            cambio = True
                    else:
                        if not usuario.is_active:
                            usuario.is_active = True
                            cambio = True

                    # Convertir nivel a float si no es None y ha cambiado
                    if nivel is not None and custom_user.nivel != float(nivel):
                        custom_user.nivel = float(nivel)
                        cambio = True

                    # Compara la empresa actual con la empresa del JSON
                    if empresa and (empresa_anterior is None or empresa_anterior.strip().lower() != empresa.strip().lower()):
                        try:
                            nueva_empresa = Empresa.objects.get(nombre=empresa)
                            custom_user.empresa = nueva_empresa
                            cambio = True
                        except Empresa.DoesNotExist:
                            print(f"Empresa con nombre {empresa} no encontrada.")

                    # Si hubo un cambio, guardar el usuario y agregarlo a la lista de actualizados
                    if cambio:
                        usuario.save()
                        custom_user.save()
                        empleados_actualizados.append({
                            'nombre': usuario.get_full_name(),
                            'correo': usuario.email,
                            'activo': usuario.is_active,
                            'activo_anterior': estado_anterior,
                            'nivel': custom_user.nivel,
                            'nivel_anterior': nivel_anterior,
                            'empresa': custom_user.empresa.nombre if custom_user.empresa else None,
                            'empresa_anterior': empresa_anterior,
                        })
                
                except User.DoesNotExist:
                    # Si no existe el usuario con ese correo
                    print(f"Usuario con correo {correo_vordcab} no encontrado.")

    return render(request, 'api/perfiles_lista.html', {'empleados_actualizados': empleados_actualizados, 'actualizado': actualizado})

@api_view(['GET'])
@authentication_classes([TokenAuthentication]) #Si quieres decargar el pdf desde el nodo desabilita este decorador de token
@permission_classes([IsAuthenticated])
def descargar_pdf_oc(request, pk):
    user = request.user
    ip_address = request.META.get('REMOTE_ADDR')
    logger.info(f"GET {request.path} by {user.first_name} {user.last_name} from {ip_address}")


    try:
        # Intentar obtener la orden de compra por su id
        compra = Compra.objects.get(id=pk)
    except Compra.DoesNotExist:
        # Si no existe la OC, devolver un mensaje de éxito con estado 200 ya que si uso 404 me manda al middleware
        return Response(
            {"detail": "La OC que intenta traer no existe, pero la solicitud fue procesada correctamente."},
            status=status.HTTP_200_OK
        )

    # Generar el PDF si la OC existe
    buf = generar_pdf(compra)

    # Devolver el PDF como respuesta
    return FileResponse(buf, as_attachment=True, filename='oc_' + str(compra.folio) + '.pdf')

@perfil_seleccionado_required
def tabla_festivos(request):
    datos = TablaFestivos.objects.all()
    
    if request.method == 'POST':
        url = 'https://vordcab.cloud/apiapp/festivos_actual/'
        api_key = 'defa1b040b2e8acf4d9ab20127e87d820eb913b9'
        #url = 'http://127.0.0.1:9000/apiapp/festivos_actual/'
        #api_key = 'f36cf2df116c3aeab68b9ee948331f382f5edcc0'
        # Hacer la solicitud a tu API de festivos
        headers = {
            'Authorization': f'Token {api_key}',
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # Procesar el JSON de la respuesta
            data = response.json()
            
            # Recorrer la lista de días festivos recibidos
            for holiday in data:
                holiday_date_str = holiday.get('dia_festivo')  # Obtener la fecha en formato YYYY-MM-DD
                if holiday_date_str:
                    # Crear o actualizar el objeto en la base de datos directamente con el formato YYYY-MM-DD
                    TablaFestivos.objects.update_or_create(dia_festivo=holiday_date_str)
            
            messages.success(request, 'Has actualizado correctamente los días festivos')
            return redirect('tabla_festivos')
        else:
            messages.error(request, 'Ocurrió un error al recibir la respuesta de la API')
    
    context = {
        'datos': datos,
    }

    return render(request, 'api/tabla_festivos.html', context)

def chatbot_view2(request):
    #print('chatbot')
    if request.method == "POST":
        #print('chatbot_post')
        user_message = request.POST.get("message", "").lower()
      
        print(user_message)

        #procesos = {
        #    "solicitud": {
        #        "pasos": (
        #           "Para hacer una solicitud en 'SAVIA 2.0', sigue estos pasos:\n"
        #            "1. Accede al módulo de **Solicitudes** desde el menú principal.\n"
        #            "2. Haz clic en el botón **Nueva Solicitud**.\n"
        #            "3. Llena el formulario con los datos requeridos.\n"
        #            "4. Adjunta los documentos necesarios.\n"
        #            "5. Haz clic en **Enviar** para guardar y enviar la solicitud."
        #        ),
        #        "video": "https://www.ejemplo.com/tutorial-solicitudes"
        #    },
        #    "reporte": {
        #        "pasos": (
        #            "Para generar un reporte:\n"
        #            "1. Ve al módulo de **Reportes**.\n"
        #            "2. Selecciona el tipo de reporte.\n"
        #            "3. Define el rango de fechas.\n"
        #            "4. Haz clic en **Generar** para descargar el reporte."
        #        ),
        #        "video": "https://www.ejemplo.com/tutorial-reportes"
        #    }
        #}

        #if "solicitud" in user_message:
        #    bot_reply = f"{procesos['solicitud']['pasos']}\n\nVideo: {procesos['solicitud']['video']}"
        #elif "reporte" in user_message:
        #    bot_reply = f"{procesos['reporte']['pasos']}\n\nVideo: {procesos['reporte']['video']}"
        #else:
        sql_generation_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role":"system",
                    "content":(
                        "Eres un experto en MySQL y conoces la estructura de la base de las tablas de SAVIA2 donde la tabla order(solicitud) está relacionada"
                        "utiliza la información dada para construir consultas SQL basada en preguntas en lenguaje natural"
                        "La relación entre tablas es dashboard_product(id) << dashboard_inventario(producto_id) << dashboard_articulosordenados(producto_id) << dashboard_order(alias: solicitud)"
                        "<< requisiciones_requis << compras_compra << entradas_entrada -- Todas los campos distrito están ligados a una tabla llamada user_distrito"
                        "En la tabla user_distrito la columna nombre es la variable del nombre del distrito.Distrito está ligado a las tablas dashboard_inventario y dashboard_order"
                        "En la tabla dashboard_inventario el importe_producto = (cantidad + cantidad_apartada) * price"
                        "En la tabla dashboard_inventario el valor_inventario =  SUM(importe_producto)"
                        "Solo genera la consulta SQL, no incluyas texto adicional. Solo SQL sintaxis por favor"
                    )
                },
                {
                    "role": "user", 
                    "content": f"Genera una consulta SQL para: {user_message}"
                }
            ],
            temperature=0,
            max_tokens=200
        )
        print(sql_generation_response)
        sql_query = sql_generation_response.choices[0].message.content
        sql_query = sql_query.replace("sql","").replace("```sql", "").replace("```", "").strip()
        print(f"Consulta SQL generada: {sql_query}")
        conn_savia2 = mysql.connector.connect(
            host='localhost', 
            user='root', 
            password='peruzzi25', 
            database='savia2'
        )
        db_cursor = conn_savia2.cursor()
            
        db_cursor.execute(sql_query)
        result = db_cursor.fetchall()
        conn_savia2.close()
        # Convertir el resultado en un formato más legible
        result_text = f"El resultado de tu consulta es: {result}"
        #bot_reply = response.choices[0].message.content
        #print(bot_reply)
                #except Exception as e:
                #    bot_reply = "I'm sorry, there was an error processing your request."

        natural_language_response =client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", "content": (
                    "Eres un asistente que convierte resultados de consultas SQL en respuestas naturales para los usuarios."
                )
                },
                {"role": "user", "content": f"El resultado del query es: {result}"}
                ],
                temperature=0.3,
                max_tokens=180
            )
        bot_reply = natural_language_response.choices[0].message.content
        print(bot_reply)
        return JsonResponse({"response": bot_reply})
    

def chatbot_view(request):
    #print('chatbot')
    if request.method == "POST":
        #print('chatbot_post')
        user_message = request.POST.get("message", "").lower()
      
        print(user_message)
        if 'status' and 'solicitud' and 'folio' and 'distrito' in user_message:
            #folio_number = 
            
            status_solicitud()
        else:
            orm_generation_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role":"system",
                        "content":(
                            "Eres un experto en Django ORM. Conoces la estructura de los modelos en un proyecto Django."
                            "Tu tarea es generar consultas utilizando el ORM de Django"
                            "Si algún modelo o relación es necesario para construir la consulta, genera las clases de modelos correspondientes."
                            "La relación entre modelos es: "
                            "dashboard.models Product(id) -> dashboard.models Inventario(FK producto_id, fields: cantidad_apartada, cantidad, price, distrito) -> dashboard.models ArticuloOrdenado(FK producto_id) -> dashboard.Order(alias: Solicitud, FK distrito_id, fields folio) -> requisiciones.models Requis(id, FK orden_id) -> compras.models Compra(id, FK req_id)"
                            "el modelo user.Distrito está relacionado con dashboard.models.Inventario y dashboard.models.Order a través de una FK llamada distrito_id."
                            "En Inventario, el valor del producto se calcula como: importe_producto = (cantidad + cantidad_apartada) * price."
                            "El valor total del inventario por distrito se calcula como: SUM(importe_producto)."
                            "Cuando se proporciona el folio de una solicitud el estatus se refiere a interpretar lo siguiente"
                            "### Reglas para Interpretar el Estado de las Solicitudes:"
                            "1. Si `order.autorizar` es `None`, describe: 'La solicitud con folio {order.folio} no ha sido autorizada aún.'"
                            "2. Si `order.autorizar` es `False`, describe: 'La solicitud con folio {order.folio} está cancelada.'"
                            "3. Si `order.autorizar` es `True`, describe: 'La solicitud con folio {order.folio} ha sido autorizada.'"
                            "\n\n"
                            "1. Si `order.requis.exists()` es `True`, recorre todas las requisiciones con un ciclo `for`."
                            "2. Recuerda que el modelo requi proviene de requisiciones.models Para cada requisición (`requi`) en `order.requis.all()`:"
                            "    a. Si `requi.autorizar` es `None`, describe: 'La requisición con folio {requi.folio} no ha sido autorizada aún.'"
                            "    b. Si `requi.autorizar` es `False`, describe: 'La requisición con folio {requi.folio} está cancelada.'"
                            "    c. Si `requi.autorizar` es `True`, describe: 'La requisición con folio {requi.folio} ha sido autorizada.'"
                            "\n\n"
                            "### Respuesta Esperada:"
                            "Siempre responde en formato de código Python utilizando el ORM de Django, los modelos ya existen solo hay que importarlos para hacer la consulta"
                            "Tu respuesta debe incluir todas las importaciones necesarias para que el código funcione correctamente. No incluyas comentarios explicativos solo código funcional"
                            "Por ejemplo, asegúrate de importar desde 'django.db.models' funciones como 'F', 'Sum', 'Count', 'Value', 'Case', etc."
                            "Siempre asigna el resultado a una variable llamada 'resultado'."
                            #"Puedes intentar desarrollar el código de un gráfico sí el usuario así lo solicita el usuario utilizando plotly y es posible"
                        )
                    },
                    {
                        "role": "user", 
                        "content": f"Genera una consulta SQL para: {user_message}"
                    }
                ],
                temperature=0,
                max_tokens=100
            )
            print(orm_generation_response)
            orm_query = orm_generation_response.choices[0].message.content
            print(orm_query)
            orm_query = orm_query.replace("```python","").replace("```","").strip()
            print(f"Consulta ORM generada: {orm_query}")
            # Paso 2: Ejecutar el código dinámicamente
            local_variables = {}
            exec(orm_query, globals(), local_variables)
            print(local_variables)
            result = local_variables.get('resultado', None)

        natural_language_response =client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", "content": (
                        "Eres un asistente que convierte resultados de consultas del ORM de Django en respuestas naturales para los usuarios"
                        "En caso de ser necesario en la respuesta se prefiere el uso de nombre que de ID's"
                        "Reproducir los status de manera completa de acuerdo al resultado"
                        "Dar formato de tabla atractivo en la medida que aplique en html"
                        #"si el campo se refiere a cantidad no es dinero por lo tanto no se formatea, si la respuesta incluye un monto o valor que se infiera que es dinero incluir formato de pesos"
                    )
                    },
                    {
                        "role": "user", "content": f"El resultado del query es: {result}"
                    }
            ],
                    temperature=0.3,
                    max_tokens=200
                )
        bot_reply = natural_language_response.choices[0].message.content
        print(bot_reply)
        return JsonResponse({"response": bot_reply})
    
def status_solicitud(folio, distrito):
    order = Order.objects.filter(folio=folio, distrito__nombre=distrito).first()

    if order:
        if order.autorizar is None:
            resultado = f'La solicitud con folio {order.folio} no ha sido autorizada aún.'
        elif order.autorizar is False:
            resultado = f'La solicitud con folio {order.folio} está cancelada.'
        elif order.autorizar is True:
            resultado = f'La solicitud con folio {order.folio} ha sido autorizada.'

            requisiciones = order.requis.all()
            for requi in requisiciones:
                if requi.autorizar is None:
                    resultado += f'\nLa requisición con folio {requi.folio} no ha sido autorizada aún.'
                elif requi.autorizar is False:
                    resultado += f'\nLa requisición con folio {requi.folio} está cancelada.'
                elif requi.autorizar is True:
                    resultado += f'\nLa requisición con folio {requi.folio} ha sido autorizada.'
    else:
        resultado = f'No se encontró la solicitud con folio {folio} en el distrito {distrito}.'