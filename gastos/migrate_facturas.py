from django.apps import apps
import mysql.connector

def migrate_facturas():
    # Obteniendo los modelos
    Solicitud_Gasto = apps.get_model('gastos', 'Solicitud_Gasto')
    Articulo_Gasto = apps.get_model('gastos', 'Articulo_Gasto')
    Factura = apps.get_model('gastos', 'Factura')

    # Iterando sobre todos los Articulo_Gasto que tengan factura_pdf y/o factura_xml
    for articulo_gasto in Articulo_Gasto.objects.filter(factura_pdf__isnull=False) | Articulo_Gasto.objects.filter(factura_xml__isnull=False):

        # Crear un diccionario para almacenar los datos de la nueva factura
        factura_data = {
            'solicitud_gasto': articulo_gasto.gasto,
            'fecha_subida': articulo_gasto.created_at
        }

        if articulo_gasto.factura_pdf:
            factura_data['archivo_pdf'] = articulo_gasto.factura_pdf

        if articulo_gasto.factura_xml:
            factura_data['archivo_xml'] = articulo_gasto.factura_xml

        # Crear el objeto Factura solo si al menos uno de los archivos (pdf o xml) existe
        if 'archivo_pdf' in factura_data or 'archivo_xml' in factura_data:
            Factura.objects.get_or_create(**factura_data)
            
        # (Opcional) Eliminar los archivos originales si se desea
        # articulo_gasto.factura_pdf.delete()
        # articulo_gasto.factura_xml.delete()
        # articulo_gasto.save()

    print("Migración completada.")

def migrar_proyecto_subproyecto():
    # Obteniendo los modelos
    #Solicitud_Gasto = apps.get_model('gastos', 'Solicitud_Gasto')
    Articulo_Gasto = apps.get_model('gastos', 'Articulo_Gasto')

    # Iterar sobre todos los Articulo_Gasto
    for articulo_gasto in Articulo_Gasto.objects.all():
        if articulo_gasto.gasto:  # Comprobando si el Articulo_Gasto tiene un objeto gasto asociado
            articulo_gasto.proyecto = articulo_gasto.gasto.proyecto
            articulo_gasto.subproyecto = articulo_gasto.gasto.subproyecto
            articulo_gasto.save()
        else:
            print(f"Articulo_Gasto con ID {articulo_gasto.id} no tiene un gasto asociado.")

    print("Migración de proyecto y subproyecto completada.")


def set_file_indices():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='*$HbAq*/4528*',
        database='SAVIA1'
    )
    cursor = conn.cursor()

    # Consultar el campo BLOB y ID
    query = "SELECT IDFACTURAGASTO, ruta_factura, ruta_xml, IDGASTO FROM SAVIA1.facturasgastostb ORDER BY IDGASTO, IDFACTURAGASTO"
    cursor.execute(query)
    rows = cursor.fetchall()

    counters = {}
    for row in rows:
        IDFACTURAGASTO, ruta_factura, ruta_xml, IDGASTO = row

        # Para cada IDGASTO, inicializar o actualizar el contador
        if IDGASTO not in counters:
            counters[IDGASTO] = {'pdf': 0, 'xml': 0}

        if ruta_factura:
            counters[IDGASTO]['pdf'] += 1
            cursor.execute("UPDATE SAVIA1.facturasgastostb SET indice=%s WHERE IDFACTURAGASTO=%s", (counters[IDGASTO]['pdf'], IDFACTURAGASTO))

        if ruta_xml:
            counters[IDGASTO]['xml'] += 1
            cursor.execute("UPDATE SAVIA1.facturasgastostb SET indice=%s WHERE IDFACTURAGASTO=%s", (counters[IDGASTO]['xml'], IDFACTURAGASTO))

    conn.commit()
    cursor.close()
    conn.close()

    print("Índices establecidos correctamente")
