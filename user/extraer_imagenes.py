import mysql.connector
import os
print("Iniciando el script...")
# Conexión a la base de datos
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='*$HbAq*/4528*',
    database='SAVIA1'
)
cursor = conn.cursor()
print("Conexión a la base de datos establecida...")
# Crear una carpeta para guardar las imágenes, si aún no existe
cursor = conn.cursor()

# Ruta para guardar las imágenes
images_path = '/home/savia/SAVIA2/static/images/imagenes_usuarios'
print(f"Verificando si existe el directorio {images_path}...")

# Crear la carpeta para guardar las imágenes, si aún no existe
if not os.path.exists(images_path):
    print(f"Creando el directorio {images_path}...")
    os.makedirs(images_path)

# Consulta para obtener el id y la imagen BLOB
cursor.execute("SELECT idusuario, foto FROM usuariostb")
print("Recuperando las imágenes de la base de datos...")
for idusuario, foto in cursor:
    print(f"Procesando la imagen para el usuario {idusuario}...")
    # Solo guardar si la imagen no es None
    if foto is not None:
       
        # Definir la ruta del archivo basándose en el id del usuario
        file_path = os.path.join(images_path, f"imagen_{idusuario}.jpg") 
        print(f"Guardando la imagen para el usuario {idusuario} en {file_path}...")

        # Guardar la imagen BLOB en un archivo
        with open(file_path, 'wb') as file:
            file.write(foto)

cursor.close()
conn.close()