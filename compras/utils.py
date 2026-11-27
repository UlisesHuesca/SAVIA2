from decimal import Decimal


CAMPOS_COMERCIALES_OC = {
    'costo_oc': 'Costo OC',
    'moneda': 'Moneda',
    'proveedor': 'Proveedor',
    'costo_fletes': 'Costo de fletes',
    'retencion': 'Retención',
    'impuestos': 'Impuestos',
}


def costo_total_historico(historico):

    cero = Decimal('0')

    return (
        (historico.costo_oc or cero)
        + (historico.impuestos or cero)
        - (historico.retencion or cero)
        + (historico.costo_fletes or cero)
    )


def obtener_correcciones_oc(compra):

    historicos = compra.history.order_by('history_date', 'history_id')

    devoluciones = []
    anterior = None
    devolucion = None

    for actual in historicos:

        # No considerar registros de eliminación
        if actual.history_type == '-':
            continue

        # Detectar devolución
        if actual.regresar_oc and (anterior is None or not anterior.regresar_oc):

            devolucion = actual

        # Detectar finalización de la corrección
        elif (devolucion is not None and not actual.regresar_oc and actual.complete):

            delta = actual.diff_against(devolucion, included_fields=list(CAMPOS_COMERCIALES_OC),)

            cambios = []

            for cambio in delta.changes:

                if cambio.field in ('proveedor', 'moneda'):
                    valor_anterior = getattr(devolucion, cambio.field)
                    valor_nuevo = getattr(actual, cambio.field)
                else:
                    valor_anterior = cambio.old
                    valor_nuevo = cambio.new

                cambios.append({
                    'campo': cambio.field,
                    'nombre': CAMPOS_COMERCIALES_OC[cambio.field],
                    'anterior': valor_anterior,
                    'nuevo': valor_nuevo,
                })
            total_anterior = costo_total_historico(devolucion)
            total_nuevo = costo_total_historico(actual)

            misma_moneda = (devolucion.moneda_id == actual.moneda_id and actual.moneda_id is not None)

            diferencia = None
            porcentaje = None

            if misma_moneda:

                diferencia = total_nuevo - total_anterior

                if total_anterior != 0:
                    porcentaje = (diferencia / total_anterior) * 100

            devoluciones.append({
                'numero': len(devoluciones) + 1,

                # Información de la devolución
                'fecha_devolucion': devolucion.history_date,
                'usuario_devolucion': devolucion.history_user,
                'comentario': devolucion.comentarios,

                # Información de la corrección
                'fecha_correccion': actual.history_date,
                'usuario_correccion': actual.history_user,

                # Detalle de modificaciones
                'cambios': cambios,
                'cantidad_cambios': len(cambios),
                'hubo_cambios': bool(cambios),

                # Información económica
                'total_anterior': total_anterior,
                'total_nuevo': total_nuevo,
                'diferencia': diferencia,
                'porcentaje': porcentaje,

                # Monedas
                'moneda_anterior': devolucion.moneda,
                'moneda_nueva': actual.moneda,
                'misma_moneda': misma_moneda,

                # Proveedores
                'proveedor_anterior': devolucion.proveedor,
                'proveedor_nuevo': actual.proveedor,
            })

            devolucion = None

        anterior = actual

    # Mostrar primero la devolución más reciente
    return devoluciones[::-1]