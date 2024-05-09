import os
import logging

def get_custom_logger(name):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logger = logging.getLogger(name)
    logger.setLevel(logging.WARNING)  # Solo loguear warnings y errores

    # Crear un handler de archivo
    file_handler = logging.FileHandler(os.path.join(BASE_DIR, 'django.log'))
    file_handler.setLevel(logging.WARNING)

    # Crear y establecer el formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s: %(message)s')
    file_handler.setFormatter(formatter)

    # Añadir el handler al logger
    logger.addHandler(file_handler)
    logger.propagate = False  # Importante para evitar la propagación a loggers de nivel superior

    return logger
