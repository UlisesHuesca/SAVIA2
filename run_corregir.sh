#!/bin/bash

echo "==============================="
echo "INICIANDO SCRIPT DE CORRECCIÓN"
echo "Fecha y hora: $(date)"
echo "==============================="

# Activar entorno virtual
source /home/savia/SAVIA2/env/bin/activate

# Ir al proyecto
cd /home/savia/SAVIA2/

# Ejecutar el comando
python manage.py corregir_articulos_para_surtir

echo "==============================="
echo "FINALIZADO"
echo "Fecha y hora: $(date)"
echo "==============================="