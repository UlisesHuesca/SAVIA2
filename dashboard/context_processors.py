from genericpath import exists
from itertools import count
from dashboard.models import ArticulosparaSurtir, Order, Inventario
from user.models import Profile
from gastos.models import Solicitud_Gasto
from tesoreria.models import Pago
from compras.models import Compra
from requisiciones.models import Requis, ValeSalidas, Devolucion
from compras.models import Compra
from viaticos.models import Solicitud_Viatico
from user.models import Profile, Tipo_perfil
from django.db.models import Q

def contadores_processor(request):
    #Por si aun no se ingresa a un perfil para que no se trabe en el login
    #usuario = Profile.objects.filter(staff__id = request.user.id)
    usuario = Profile.objects.filter(staff__id=request.user.id)

    conteo_requis = 0
    conteo_oc = 0
    conteo_pagos = 0
    conteo_solicitudes = 0
    conteo_requis_pendientes = 0
    conteo_salidas = 0
    conteo_oc1 = 0
    conteo_entradas = 0
    conteo_gastos_pendientes = 0
    conteo_gastos_gerencia = 0
    conteo_viaticos = 0
    conteo_viaticos_gerencia = 0
    conteo_asignar_montos = 0
    conteo_viaticos_pagar= 0
    conteo_gastos_pagar= 0 
    conteo_asignar_montos = 0
    conteo_viaticos=0
    conteo_devoluciones = 0
    
    conteo_usuario = Profile.objects.all().count()
    conteo_productos = Inventario.objects.filter(cantidad__gt = 0).count()
    solicitudes_generadas = Order.objects.filter(complete = True).count()




    if not usuario:
        #Profile.objects.filter(staff__id=request.user.id):
        #productos= ArticulosparaSurtir.objects.filter(salida=False, articulos__orden__autorizar = True, articulos__producto__producto__servicio = False, articulos__orden__tipo__tipo="normal")
        #ordenes_por_autorizar = Order.objects.filter(complete=True, autorizar=None)
        conteo = 0
        conteo_ordenes = 0
        usuario = None
    else:
        #productos= ArticulosparaSurtir.objects.filter(salida=False, articulos__orden__autorizar = True, articulos__producto__producto__servicio = False, articulos__orden__tipo__tipo="normal")
        #productos= productos.filter(articulos__orden__superintendente=usuario)
        ordenes = Order.objects.filter(complete=True, autorizar = True)

        requis = Requis.objects.filter(complete = True)
        conteo = requis.count()
        usuario = usuario[0]

        if usuario.tipo.compras == True:
            requis= Requis.objects.filter(complete=True, autorizar=True, colocada=False)
            conteo_requis = requis.count()
        if usuario.tipo.oc_superintendencia == True:
            oc = Compra.objects.filter(complete = True, autorizado1 = None, autorizado2= None)
            conteo_oc1 = oc.count()
        if usuario.tipo.oc_gerencia == True:
            oc = Compra.objects.filter(autorizado1= True, autorizado2 = None)
            gastos_gerencia = Solicitud_Gasto.objects.filter(complete=True, autorizar=True, autorizar2=None)
            viaticos_gerencia = Solicitud_Viatico.objects.filter(complete = True, autorizar=True, autorizar2=None, montos_asignados=True)
            devoluciones = Devolucion.objects.filter(complete = True, autorizada = None)
            conteo_oc = oc.count()
            conteo_viaticos_gerencia = viaticos_gerencia.count()
            conteo_gastos_gerencia = gastos_gerencia.count()
            conteo_devoluciones = devoluciones.count()
        if usuario.tipo.tesoreria == True:
            oc_pendientes = Compra.objects.filter(pagada=False, autorizado2=True)
            viaticos_por_asignar = Solicitud_Viatico.objects.filter(complete = True, autorizar=True, montos_asignados=False)
            gastos_por_pagar = Solicitud_Gasto.objects.filter(complete=True, autorizar2= True, pagada=False )
            viaticos_por_pagar = Solicitud_Viatico.objects.filter(complete = True, autorizar2=True, pagada=False)
            conteo_viaticos_pagar = viaticos_por_pagar.count()
            conteo_gastos_pagar = gastos_por_pagar.count()
            conteo_pagos = oc_pendientes.count()
            conteo_asignar_montos = viaticos_por_asignar.count()
        if usuario.tipo.supervisor == True:
            solicitudes_pendientes = Order.objects.filter(autorizar = None, complete = True, supervisor=usuario)
            conteo_solicitudes = solicitudes_pendientes.count()
        if usuario.tipo.superintendente == True:
            requisiciones_pendientes = Requis.objects.filter(complete=True, autorizar=None, orden__superintendente = usuario)
            gastos = Solicitud_Gasto.objects.filter(complete=True, autorizar=None, superintendente = usuario)
            ids_gastos_validados = [gasto.id for gasto in gastos if gasto.get_validado]
            gastos_pendientes = Solicitud_Gasto.objects.filter(id__in=ids_gastos_validados)
            viaticos_pendientes = Solicitud_Viatico.objects.filter(complete =True, autorizar = None, superintendente = usuario)
            conteo_requis_pendientes = requisiciones_pendientes.count()
            conteo_gastos_pendientes = gastos_pendientes.count()
            conteo_viaticos = viaticos_pendientes.count()
        if usuario.tipo.almacen == True:
            entradas = Compra.objects.filter(Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True), solo_servicios= False, entrada_completa = False, autorizado2= True).order_by('-folio')
            conteo_entradas = entradas.count()
        else:
            entradas = Compra.objects.filter(Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True), solo_servicios= True, entrada_completa = False, autorizado2= True, req__orden__staff = usuario).order_by('-folio')
            conteo_entradas = entradas.count()


    return {
    'conteo_devoluciones': conteo_devoluciones,
    'solicitudes_generadas':solicitudes_generadas,
    'conteo_productos':conteo_productos,
    'conteo_usuario':conteo_usuario,
    'conteo_viaticos_pagar':conteo_viaticos_pagar,
    'conteo_gastos_pagar':conteo_gastos_pagar,
    'conteo_asignar_montos':conteo_asignar_montos,
    'conteo_viaticos': conteo_viaticos,
    'conteo_viaticos_gerencia':conteo_viaticos_gerencia,
    'conteo_requis_pendientes':conteo_requis_pendientes,
    'conteo_entradas':conteo_entradas,
    'conteo_gastos_gerencia':conteo_gastos_gerencia,
    'conteo_solicitudes': conteo_solicitudes,
    'conteodeordenes':conteo,
    'conteo_gastos_pendientes':conteo_gastos_pendientes,
    'conteo_oc': conteo_oc,
    'conteo_oc1':conteo_oc1,
    'usuario':usuario,
    'conteo_requis': conteo_requis,
    'conteo_pagos':conteo_pagos,
    }