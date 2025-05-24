from genericpath import exists
from itertools import count
from dashboard.models import ArticulosparaSurtir, Order, Inventario
from user.models import Profile
from gastos.models import Solicitud_Gasto, ValeRosa
from tesoreria.models import Pago
from compras.models import Compra
from requisiciones.models import Requis, ValeSalidas, Devolucion
from compras.models import Compra, Proveedor
from viaticos.models import Solicitud_Viatico
from user.models import Profile, Tipo_perfil
from django.db.models import Q
from django.conf import settings
from django.utils import translation

def contadores_processor(request):
    #Por si aun no se ingresa a un perfil para que no se trabe en el login
    #usuario = Profile.objects.filter(staff__id = request.user.id)
    pk = request.session.get('selected_profile_id')
    try:
        usuario = Profile.objects.get(id=pk)
    except Profile.DoesNotExist:
        usuario = None

    #print("Idioma en sesión al cargar la página:", request.session.get(settings.LANGUAGE_SESSION_KEY))
    language = request.session.get(settings.LANGUAGE_SESSION_KEY, settings.LANGUAGE_CODE)
    translation.activate(language)

    conteo_requis = 0
    conteo_oc = 0
    conteo_pagos = 0
    conteo_solicitudes = 0
    conteo_requis_pendientes = 0
    conteo_servicios = 0
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
    conteo_ordenes = 0
    conteo_pagos2 = 0
    proveedores_altas = 0
    conteo_vales = 0
    
    conteo_usuario = Profile.objects.filter(st_activo = True).count()
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
        #if usuario.staff.staff.is_staff:
            #requis.
        if usuario.tipo.compras == True:
            requis= Requis.objects.filter(orden__distrito = usuario.distritos, autorizar=True, colocada=False, complete = True)
            conteo_requis = requis.count()

        if usuario.tipo.subdirector == True:
            oc = Compra.objects.filter(complete = True, autorizado1 = None, autorizado2= None, req__orden__superintendente = usuario)
            conteo_oc1 = oc.count()
            gastos = Solicitud_Gasto.objects.filter(complete=True, autorizar=None, superintendente = usuario, distrito = usuario.distritos)
            conteo_gastos_pendientes = gastos.count()
            viaticos_pendientes = Solicitud_Viatico.objects.filter(complete =True, autorizar = None, superintendente = usuario, distrito = usuario.distritos)
            conteo_viaticos = viaticos_pendientes.count()
            viaticos_gerencia = Solicitud_Viatico.objects.filter(complete = True, autorizar=True, autorizar2=None, montos_asignados=True, distrito = usuario.distritos, superintendente = usuario)
            conteo_viaticos_gerencia = viaticos_gerencia.count()
            vales_rosa = ValeRosa.objects.filter(esta_aprobado = None, gasto__complete = True, gasto__autorizar2 = True, gasto__superintendente = usuario)
            conteo_vales = vales_rosa.count()
        elif usuario.tipo.oc_superintendencia == True:
            oc = Compra.objects.filter(complete=True, autorizado1= None, req__orden__distrito = usuario.distritos)
            oc_pendientes = Compra.objects.filter(pagada=False, autorizado2=True, req__orden__distrito = usuario.distritos)
            devoluciones = Devolucion.objects.filter(complete=True, autorizada=None, solicitud__distrito = usuario.distritos)
            conteo_oc1 = oc.count()
            conteo_devoluciones = devoluciones.count()
            conteo_pagos2 = oc_pendientes.count()
            conteo_vales = vales_rosa.count()
        
        if usuario.tipo.oc_gerencia == True:
            oc = Compra.objects.filter(autorizado1= True, autorizado2 = None, req__orden__distrito = usuario.distritos)
            gastos_gerencia = Solicitud_Gasto.objects.filter(complete=True, autorizar=True, autorizar2=None, distrito = usuario.distritos)
            viaticos_gerencia = Solicitud_Viatico.objects.filter(complete=True, autorizar = True, montos_asignados=True, autorizar2 = None, distrito = usuario.distritos, superintendente = usuario)
            vales_rosa = ValeRosa.objects.filter(esta_aprobado = None, gasto__complete = True, gasto__autorizar2 = True, gasto__autorizado_por2 = usuario ).order_by('-gasto__folio')
            conteo_oc = oc.count()
            conteo_viaticos_gerencia = viaticos_gerencia.count()
            conteo_gastos_gerencia = gastos_gerencia.count()
           
        if usuario.tipo.tesoreria == True:
            oc_pendientes = Compra.objects.filter(pagada=False, para_pago = True, autorizado2=True, req__orden__distrito = usuario.distritos)
            viaticos_por_asignar = Solicitud_Viatico.objects.filter(complete = True, autorizar=True, montos_asignados=False, distrito = usuario.distritos)
            gastos_por_pagar = Solicitud_Gasto.objects.filter(complete=True, autorizar2= True, pagada=False, distrito = usuario.distritos  )
            viaticos_por_pagar = Solicitud_Viatico.objects.filter(complete = True, autorizar2=True, pagada=False, distrito = usuario.distritos)
            conteo_viaticos_pagar = viaticos_por_pagar.count()
            conteo_gastos_pagar = gastos_por_pagar.count()
            conteo_pagos = oc_pendientes.count()
            conteo_asignar_montos = viaticos_por_asignar.count()
        if usuario.tipo.supervisor == True:
            solicitudes_pendientes = Order.objects.filter(autorizar = None, complete = True, supervisor=usuario)
            conteo_solicitudes = solicitudes_pendientes.count()

        if usuario.distritos.nombre == "MATRIZ" or usuario.distritos.nombre == "BRASIL" and usuario.tipo.supervisor:   
           requis = Requis.objects.filter(autorizar=None, complete =True).filter(Q(orden__supervisor=usuario) & Q(orden__tipo__tipo = 'normal') | Q(orden__superintendente=usuario) & Q(orden__tipo__tipo = 'resurtimiento'))
        elif usuario.tipo.superintendente == True and usuario.tipo.nombre != "Admin":
            requis = Requis.objects.filter(autorizar=None, orden__superintendente=usuario, complete =True)
            #requisiciones_pendientes = Requis.objects.filter(complete=True, autorizar=None, orden__superintendente = usuario)
            
        
        elif usuario.tipo.nombre == "Admin":
            requis = Requis.objects.filter(autorizar=None, complete = True, orden__distrito = usuario.distritos)


        gastos = Solicitud_Gasto.objects.filter(complete=True, autorizar=None, superintendente = usuario, distrito = usuario.distritos)
        ids_gastos_validados = [gasto.id for gasto in gastos if gasto.get_validado]
        gastos_pendientes = Solicitud_Gasto.objects.filter(id__in=ids_gastos_validados)
        viaticos_pendientes = Solicitud_Viatico.objects.filter(complete =True, autorizar = None, superintendente = usuario, distrito = usuario.distritos)
        
        conteo_requis_pendientes = requis.count()
        conteo_gastos_pendientes = gastos_pendientes.count()
        conteo_viaticos = viaticos_pendientes.count()
      
        if usuario.tipo.nombre == 'Admin':
            entradas = Compra.objects.filter(Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True) |Q(monto_pagado__gt=0), req__orden__distrito = usuario.distritos, entrada_completa = False, autorizado2= True, solo_servicios = False)
            servicios = Compra.objects.filter(Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True) |Q(monto_pagado__gt=0), req__orden__distrito = usuario.distritos, solo_servicios= True, entrada_completa = False, autorizado2= True)         
        else:
            entradas = Compra.objects.filter(
            Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True) |Q(monto_pagado__gt=0),
            Q(solo_servicios=False) | (Q(solo_servicios=False) & Q(req__orden__staff=usuario)),
            req__orden__distrito = usuario.distritos,  
            entrada_completa = False, 
            autorizado2= True)
            servicios = Compra.objects.filter(Q(cond_de_pago__nombre ='CREDITO') | Q(pagada = True) |Q(monto_pagado__gt=0), solo_servicios= True, entrada_completa = False, autorizado2= True, req__orden__staff = usuario)
        conteo_entradas = entradas.count()
        conteo_servicios = servicios.count()

        if usuario.tipo.proveedores_edicion == True:
            proveedores_altas = Proveedor.objects.filter(
            completo=True, 
            direcciones__estatus__nombre = "PREALTA",
            ).exclude(familia__nombre="IMPUESTOS").distinct().count()

    return {
    
    'proveedores_altas':proveedores_altas,
    'conteo_pagos2': conteo_pagos2,
    'conteo_devoluciones': conteo_devoluciones,
    'solicitudes_generadas':solicitudes_generadas,
    'conteo_productos':conteo_productos,
    'conteo_usuario':conteo_usuario,
    'conteo_viaticos_pagar':conteo_viaticos_pagar,
    'conteo_gastos_pagar':conteo_gastos_pagar,
    'conteo_servicios':conteo_servicios,
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
    'conteo_vales':conteo_vales,
    }

 