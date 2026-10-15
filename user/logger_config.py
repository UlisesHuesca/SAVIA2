import os
import logging


def get_custom_logger(name):
    BASE_DIR = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    logger = logging.getLogger(name)
    logger.setLevel(logging.WARNING)

    log_path = os.path.join(BASE_DIR, 'django.log')

    # Evitar agregar varias veces el mismo FileHandler
    if not any(
        isinstance(handler, logging.FileHandler)
        and handler.baseFilename == os.path.abspath(log_path)
        for handler in logger.handlers
    ):
        file_handler = logging.FileHandler(
            log_path,
            encoding='utf-8'
        )

        file_handler.setLevel(logging.WARNING)

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s: %(message)s'
        )

        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False

    return logger