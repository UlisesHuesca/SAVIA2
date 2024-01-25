from compras.models import Compra
from tesoreria.models import Pago
from gastos.models import Solicitud_Gasto
from django.db.models import F, Sum, Q
import mysql.connector
from collections import defaultdict


def verificar_compras_colocadas():
    print('Procesando...')
    # Obtener todas las compras que cumplen con las condiciones
    compras = Compra.objects.filter(autorizado2=True, pagada=False)
    print(f"Encontradas {compras.count()} compras para verificar.")
    
    count = 0
    for compra in compras:
        # Obtener la suma de los montos de los pagos relacionados con la compra
        total = Pago.objects.filter(oc=compra).aggregate(cantidad_sumada=Sum('monto'))
        
        monto_total = total['cantidad_sumada'] if total['cantidad_sumada'] is not None else 0
        
        if monto_total >= compra.costo_oc:  # Asumiendo que "monto" es el campo de la Compra con el monto total
            count += 1
            print(f"Compra con ID: {compra.id} ha sido marcada como pagada. {count}")
            compra.pagada = True
            compra.save()

#verificar_compras_colocadas()
def verificar_gastos_pagados():
    print('Procesando...')
    # Obtener todas las compras que cumplen con las condiciones
    gastos = Solicitud_Gasto.objects.filter(autorizar2=True, pagada=False)
    print(f"Encontradas {gastos.count()} gastos para verificar.")
    
    count = 0
    for gasto in gastos:
        # Obtener la suma de los montos de los pagos relacionados con la compra
        total = Pago.objects.filter(gasto=gasto).aggregate(cantidad_sumada=Sum('monto'))
        monto_total = total['cantidad_sumada'] if total['cantidad_sumada'] is not None else 0
        
        if monto_total >= gasto.get_total_solicitud:  # Asumiendo que "monto" es el campo de la Compra con el monto total
            count += 1
            print(f"Gasto con ID: {gasto.id} ha sido marcada como pagada. {count}")
            gasto.pagada = True
            gasto.save()

#verificar_compras_colocadas()
def actualizar_gastos_factura_con_xml():
    # Establecer la conexión con la base de datos SAVIA1
    conn_savia1 = mysql.connector.connect(
        host='localhost',
        user='root',
        password='*$HbAq*/4528*',
        database='SAVIA1'
    )
    cursor_savia1 = conn_savia1.cursor()

    # Establecer la conexión con la base de datos savia2_default
    conn_savia2_default = mysql.connector.connect(
        host='localhost',
        user='root',
        password='*$HbAq*/4528*',
        database='savia2_default'
    )
    cursor_savia2_default = conn_savia2_default.cursor()

    # Obtener pares únicos de IDGASTO y IDFACTURAGASTO
    cursor_savia1.execute("""
        SELECT DISTINCT IDGASTO, IDFACTURAGASTO, ruta_xml 
        FROM facturasgastostb 
        WHERE ruta_xml IS NOT NULL
        ORDER BY IDGASTO, IDFACTURAGASTO
    """)
    pares_unicos = cursor_savia1.fetchall()

    # Actualizar gastos_factura con cada par único
    for idgasto, idfacturagasto, ruta_xml in pares_unicos:
        cursor_savia2_default.execute("""
            UPDATE gastos_factura 
            SET archivo_xml = %s 
            WHERE solicitud_gasto_id = %s AND archivo_xml IS NULL
            LIMIT 1
        """, (ruta_xml, idgasto))

    # Confirmar los cambios
    conn_savia2_default.commit()

    # Cerrar las conexiones
    cursor_savia1.close()
    conn_savia1.close()
    cursor_savia2_default.close()
    conn_savia2_default.close()

    print("Actualización de gastos_factura completada")

     