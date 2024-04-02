from compras.models import Compra
from tesoreria.models import Pago
from gastos.models import Solicitud_Gasto
from django.db.models import F, Sum, Q
import mysql.connector
from collections import defaultdict
import os


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


def actualizar_gastos_factura_con_pdf():
    conn_savia1 = mysql.connector.connect(
        host='localhost', 
        user='root', 
        password='*$HbAq*/4528*', 
        database='SAVIA1'
    )
    cursor_savia1 = conn_savia1.cursor()

    conn_savia2_default = mysql.connector.connect(
        host='localhost', 
        user='root', 
        password='*$HbAq*/4528*', 
        database='savia2_default'
    )
    cursor_savia2_default = conn_savia2_default.cursor()

    consulta_facturas = """
    SELECT f.IDGASTO, f.indice, f.ruta_factura
    FROM facturasgastostb f
    JOIN gastostb g ON g.IDGASTO = f.IDGASTO
    WHERE f.ruta_factura IS NOT NULL AND f.IDGASTO > 16349 AND g.IDALMACEN = 3
    ORDER BY f.IDGASTO, f.indice;
    """
    cursor_savia1.execute(consulta_facturas)
    facturas = cursor_savia1.fetchall()

    idgasto_actual = None

    for idgasto, indice, ruta_factura in facturas:
        if idgasto_actual != idgasto:
            idgasto_actual = idgasto
            # Obtener todos los registros de gastos_factura para el IDGASTO actual
            cursor_savia2_default.execute("""
                SELECT id FROM gastos_factura WHERE solicitud_gasto_id = %s ORDER BY id;
            """, (idgasto + 2000,))
            gastos_ids = cursor_savia2_default.fetchall()
            print(gastos_ids)

        # Asumiendo que el indice corresponde al orden de los registros obtenidos
        if indice - 1 < len(gastos_ids):
            gasto_id = gastos_ids[indice - 1][0]  # Obtiene el id basado en el índice
            cursor_savia2_default.execute("""
                UPDATE gastos_factura SET archivo_pdf = %s WHERE id = %s;
            """, (ruta_factura, gasto_id))
            print(ruta_factura, gasto_id)

    conn_savia2_default.commit()

    cursor_savia1.close()
    conn_savia1.close()
    cursor_savia2_default.close()
    conn_savia2_default.close()

    print("Las actualizaciones se han completado.")

def actualizar_gastos_factura_con_xml():
    conn_savia1 = mysql.connector.connect(
        host='localhost', 
        user='root', 
        password='*$HbAq*/4528*',  # Cambia [TU_PASSWORD] por la contraseña real
        database='SAVIA1'
    )
    cursor_savia1 = conn_savia1.cursor()

    conn_savia2_default = mysql.connector.connect(
        host='localhost', 
        user='root', 
        password='*$HbAq*/4528*',  # Cambia [TU_PASSWORD] por la contraseña real
        database='savia2_default'
    )
    cursor_savia2_default = conn_savia2_default.cursor()

    consulta_facturas = """
    SELECT f.IDGASTO, f.indice, f.ruta_xml  # Asumiendo que existe ruta_xml en la tabla
    FROM facturasgastostb f
    JOIN gastostb g ON g.IDGASTO = f.IDGASTO
    WHERE f.ruta_xml IS NOT NULL AND f.IDGASTO > 16349 AND g.IDALMACEN = 3
    ORDER BY f.IDGASTO, f.indice;
    """
    cursor_savia1.execute(consulta_facturas)
    facturas = cursor_savia1.fetchall()

    idgasto_actual = None

    for idgasto, indice, ruta_xml in facturas:
        if idgasto_actual != idgasto:
            idgasto_actual = idgasto
            cursor_savia2_default.execute("""
                SELECT id FROM gastos_factura WHERE solicitud_gasto_id = %s ORDER BY id;
            """, (idgasto + 2000,))
            gastos_ids = cursor_savia2_default.fetchall()
            print(gastos_ids)

        if indice - 1 < len(gastos_ids):
            gasto_id = gastos_ids[indice - 1][0]  # Obtiene el id basado en el índice
            #if gasto_id not in (19095, 19096):  # Excluir los ids no deseados
            cursor_savia2_default.execute("""
            UPDATE gastos_factura SET archivo_xml = %s WHERE id = %s;
            """, (ruta_xml, gasto_id))
            print(ruta_xml, gasto_id)

    conn_savia2_default.commit()

    cursor_savia1.close()
    conn_savia1.close()
    cursor_savia2_default.close()
    conn_savia2_default.close()

    print("Las actualizaciones de XML se han completado.")

# No olvides cambiar '[TU_PASSWORD]' por tu contraseña real antes de ejecutar el script.


def actualizar_gastos_factura_con_xml_general():
    conn_savia1 = mysql.connector.connect(
        host='localhost', 
        user='root', 
        password='*$HbAq*/4528*',  # Asegúrate de usar la contraseña correcta
        database='SAVIA1'
    )
    cursor_savia1 = conn_savia1.cursor()

    conn_savia2_default = mysql.connector.connect(
        host='localhost', 
        user='root', 
        password='*$HbAq*/4528*',  # Asegúrate de usar la contraseña correcta
        database='savia2_default'
    )
    cursor_savia2_default = conn_savia2_default.cursor()

    consulta_facturas = """
    SELECT f.IDGASTO, f.indice, f.ruta_xml
    FROM facturasgastostb f
    JOIN gastostb g ON g.IDGASTO = f.IDGASTO
    WHERE f.ruta_xml IS NOT NULL AND f.IDGASTO <= 16349
    ORDER BY f.IDGASTO, f.indice;
    """
    cursor_savia1.execute(consulta_facturas)
    facturas = cursor_savia1.fetchall()

    for idgasto, indice, ruta_xml in facturas:
        # Obtén el gasto_id basado en el IDGASTO y el índice proporcionado
        cursor_savia2_default.execute("""
            SELECT id FROM gastos_factura WHERE solicitud_gasto_id = %s ORDER BY id LIMIT %s,1;
        """, (idgasto, indice - 1))  # Ajusta el OFFSET según el índice
        gasto_factura = cursor_savia2_default.fetchone()

        if gasto_factura:
            gasto_id = gasto_factura[0]
            cursor_savia2_default.execute("""
                UPDATE gastos_factura SET archivo_xml = %s WHERE id = %s;
            """, (ruta_xml, gasto_id))
            print(ruta_xml, gasto_id)

    conn_savia2_default.commit()

    cursor_savia1.close()
    conn_savia1.close()
    cursor_savia2_default.close()
    conn_savia2_default.close()

    print("Las actualizaciones de XML se han completado.")




def migrate_blob_to_files():
    # Establecer conexión con la base de datos
    conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='peruzzi25',
    database='savia_activo'
    )
    cursor = conn.cursor()
    #Se crea el directorio
    if not os.path.exists('media/comprobantes/'):
        os.makedirs('media/comprobantes/')

    # Consultar el campo BLOB
    query = "SELECT IDPAGO, FOLIO, COMPROBANTE FROM savia_activo.pagostb"
    cursor.execute(query)
    rows = cursor.fetchall()

    for row in rows:
        IDPAGO, FOLIO, COMPROBANTE = row
        

        # Verifica si comprobante_blob no es None
        if COMPROBANTE is not None:
        # Define el nombre del archivo y la ruta
            file_name = f"{IDPAGO}.pdf"  # Suponiendo que es un PDF, ajusta si es necesario
            path = f"media/comprobantes/{file_name}"
        
            #Guarda el BLOB como archivo físico
            with open(path, 'wb') as file:
                file.write(COMPROBANTE)

            # Actualiza la columna con la ruta del archivo en la base de datos
            cursor.execute("UPDATE savia_activo.pagostb SET ruta_comprobante=%s WHERE IDPAGO=%s", (path, IDPAGO))
        else:
            print(f"El registro con ID {IDPAGO} tiene un comprobante BLOB nulo o vacío.")   

    conn.commit()
    cursor.close()
    conn.close()

    print("Migración completada")

def migrate_compras_to_directory():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='peruzzi25',
        database='savia_activo'
    )
    cursor = conn.cursor()

    # Consultar el campo BLOB
    query = "SELECT IDFACTURACOMPRA, FACTURA, XML, IDCOMPRA FROM savia_activo.facturascomprastb ORDER BY IDCOMPRA, IDFACTURACOMPRA"
    cursor.execute(query)
    rows = cursor.fetchall()

    counters = {}
    for row in rows:
        IDFACTURACOMPRA, FACTURA, XML, IDCOMPRA = row

        # Para cada IDCOMPRA, inicializar o actualizar el contador
        if IDCOMPRA not in counters:
            counters[IDCOMPRA] = {'pdf': 0, 'xml': 0}

        if FACTURA:
            counters[IDCOMPRA]['pdf'] += 1
            indice = counters[IDCOMPRA]['pdf']
            file_name = f"{IDCOMPRA}-PDF-{counters[IDCOMPRA]['pdf']}.pdf"
            path = f"facturas/{file_name}"
            with open(path, 'wb') as file:
                file.write(FACTURA)
            cursor.execute("UPDATE savia_activo.facturascomprastb SET ruta_factura=%s, indice=%s WHERE IDFACTURACOMPRA=%s", (path, indice, IDFACTURACOMPRA))

        if XML:
            counters[IDCOMPRA]['xml'] += 1
            indice = counters[IDCOMPRA]['xml']
            file_name = f"{IDCOMPRA}-XML-{counters[IDCOMPRA]['xml']}.xml"
            path = f"xml/{file_name}"
            with open(path, 'wb') as file:
                file.write(XML)
            cursor.execute("UPDATE savia_activo.facturascomprastb SET ruta_xml=%s, indice=%s WHERE IDFACTURACOMPRA=%s", (path, indice, IDFACTURACOMPRA))

    conn.commit()
    cursor.close()
    conn.close()

    print("Migración completada")

def migrate_gastosfacturas_to_files():
    # Establecer conexión con la base de datos
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='peruzzi25',
        database='savia_activo'
    )
    cursor = conn.cursor()
    print('Iniciando proceso')
    # Crear el directorio si no existe
    directory = 'media/'
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Consultar los campos BLOB
    query = "SELECT IDGASTO, PDF, PDFCOMPROBACION, FACTURA, XML FROM savia_activo.gastostb"
    cursor.execute(query)
    rows = cursor.fetchall()

    for row in rows:
        IDGASTO, PDF, PDFCOMPROBACION, FACTURA, XML = row
        
        # Guardar PDF
        if PDF is not None:
            pdf_path = f"{directory}/gastos_pdf/PDF_ID{IDGASTO}.pdf"
            pdf_path_r = f"/gastos_pdf/PDF_ID{IDGASTO}.pdf"
            with open(pdf_path, 'wb') as file:
                file.write(PDF)
            cursor.execute("UPDATE savia_activo.gastostb SET ruta_pdf=%s WHERE IDGASTO=%s", (pdf_path_r, IDGASTO))

        #Guarda comprabación
        if PDFCOMPROBACION is not None:
            pdfc_path = f"{directory}/gastos_comprobacion/PDFC_ID{IDGASTO}.pdf"
            pdfc_path_r = f"/gastos_comprobacion/PDFC_ID{IDGASTO}.pdf"
            with open(pdfc_path, 'wb') as file:
                file.write(PDFCOMPROBACION)
            cursor.execute("UPDATE savia_activo.gastostb SET ruta_comprobacion = %s WHERE IDGASTO=%s",(pdfc_path_r, IDGASTO))

        # Guardar FACTURA
        if FACTURA is not None:
            factura_path = f"{directory}/gastos_factura/FACTURA_ID{IDGASTO}.pdf"
            factura_path_r = f"/gastos_factura/FACTURA_ID{IDGASTO}.pdf"
            with open(factura_path, 'wb') as file:
                file.write(FACTURA)
            cursor.execute("UPDATE savia_activo.gastostb SET ruta_factura=%s WHERE IDGASTO=%s", (factura_path_r,IDGASTO))
        
        # Guardar XML
        if XML is not None:
            xml_path = f"{directory}/gastos_xml/XML_ID{IDGASTO}.xml"
            xml_path_r = f"/gastos_xml/XML_ID{IDGASTO}.xml"
            with open(xml_path, 'wb') as file:
                file.write(XML)
            cursor.execute("UPDATE savia_activo.gastostb SET ruta_xml=%s WHERE IDGASTO=%s", (xml_path_r, IDGASTO))

    conn.commit()
    cursor.close()
    conn.close()

    print("Migración completada")


def get_file_type_from_signature(blob_data):
    if blob_data.startswith(b'%PDF-'):
        return 'pdf'
    elif blob_data.startswith(b'<?xml'):
        return 'xml'
    elif blob_data[:4] == b'\xFF\xD8\xFF\xE0':
        return 'jpg'
    # Agrega más condiciones aquí para otros tipos de archivo
    else:
        return 'unknown'

def process_db_records():
    # Conexión a la base de datos y obtención de los primeros 10 registros
    import mysql.connector

    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='peruzzi25',
        database='saviauno'
    )
    cursor = conn.cursor()

    query = "SELECT FACTURA FROM saviados.gastostb LIMIT 100,200"
    cursor.execute(query)
    rows = cursor.fetchall()

    for row in rows:
        for data in row:
            if data:
                print(get_file_type_from_signature(data))

    cursor.close()
    conn.close()

def migrate_tablafacturasgastos_to_files():
    # Establecer conexión con la base de datos
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='peruzzi25',
        database='savia_activo'
    )
    cursor = conn.cursor()
    
    # Crear el directorio si no existe
    directory = 'media/'
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Consultar los campos BLOB
    query = "SELECT IDFACTURAGASTO, FACTURA, XML, IDGASTO FROM savia_activo.facturasgastostb"
    cursor.execute(query)
    rows = cursor.fetchall()

    for row in rows:
        IDFACTURAGASTO, FACTURA, XML, IDGASTO = row
        
        #Guardar FACTURA
        if FACTURA is not None:
            factura_path = f"{directory}/gastos_facturatb/FACTURA_{IDFACTURAGASTO}_{IDGASTO}.pdf"
            factura_path_r = f"/gastos_facturatb/FACTURA_{IDFACTURAGASTO}_{IDGASTO}.pdf"
            with open(factura_path, 'wb') as file:
                file.write(FACTURA)
            cursor.execute("UPDATE savia_activo.facturasgastostb SET ruta_factura=%s WHERE IDFACTURAGASTO=%s ", (factura_path_r,IDFACTURAGASTO))
        
        # Guardar XML
        if XML is not None:
            xml_path = f"{directory}/gastos_xmltb/XML_{IDFACTURAGASTO}_{IDGASTO}.xml"
            xml_path_r =f"/gastos_xmltb/XML_{IDFACTURAGASTO}_{IDGASTO}.xml"
            with open(xml_path, 'wb') as file:
                file.write(XML)
            cursor.execute("UPDATE savia_activo.facturasgastostb SET ruta_xml=%s WHERE IDFACTURAGASTO=%s", (xml_path_r, IDFACTURAGASTO))

    conn.commit()
    cursor.close()
    conn.close()

    print("Migración completada")



def migrate_tablafacturasgastos_to_files_v2():
    # Establecer conexión con la base de datos
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='peruzzi25',
        database='savia_activo'
    )
    cursor = conn.cursor()
    
    # Crear el directorio si no existe
    directory = 'media/'
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Consultar los campos BLOB
    query = "SELECT IDFACTURAGASTO, FACTURA, XML, IDGASTO FROM savia_activo.facturasgastostb ORDER BY IDGASTO, IDFACTURAGASTO"
    cursor.execute(query)
    rows = cursor.fetchall()

    # Diccionarios para manejar los índices de cada IDGASTO
    indice_factura_por_idgasto = {}
    indice_xml_por_idgasto = {}

    for row in rows:
        IDFACTURAGASTO, FACTURA, XML, IDGASTO = row
        
        # Incrementar o inicializar índice para FACTURA si existe
        if FACTURA is not None:
            if IDGASTO not in indice_factura_por_idgasto:
                indice_factura_por_idgasto[IDGASTO] = 1
            else:
                indice_factura_por_idgasto[IDGASTO] += 1

            factura_path = f"{directory}gastos_facturatb/FACTURA_{IDGASTO}_{indice_factura_por_idgasto[IDGASTO]}.pdf"
            factura_path_r = f"/gastos_facturatb/FACTURA_{IDGASTO}_{indice_factura_por_idgasto[IDGASTO]}.pdf"
            with open(factura_path, 'wb') as file:
                file.write(FACTURA)
            cursor.execute("UPDATE savia_activo.facturasgastostb SET ruta_factura=%s, indice=%s WHERE IDFACTURAGASTO=%s", (factura_path_r, indice_factura_por_idgasto[IDGASTO], IDFACTURAGASTO))
        
        # Incrementar o inicializar índice para XML si existe
        if XML is not None:
            if IDGASTO not in indice_xml_por_idgasto:
                indice_xml_por_idgasto[IDGASTO] = 1
            else:
                indice_xml_por_idgasto[IDGASTO] += 1

            xml_path = f"{directory}gastos_xmltb/XML_{IDGASTO}_{indice_xml_por_idgasto[IDGASTO]}.xml"
            xml_path_r = f"/gastos_xmltb/XML_{IDGASTO}_{indice_xml_por_idgasto[IDGASTO]}.xml"
            with open(xml_path, 'wb') as file:
                file.write(XML)
            cursor.execute("UPDATE savia_activo.facturasgastostb SET ruta_xml=%s, indice=%s WHERE IDFACTURAGASTO=%s", (xml_path_r, indice_xml_por_idgasto[IDGASTO], IDFACTURAGASTO))

    conn.commit()
    cursor.close()
    conn.close()

    print("Migración completada")

