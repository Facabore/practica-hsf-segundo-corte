"""Configuración de logging: consola + archivo, con fecha/hora, nivel, evento y resultado."""

import logging
from logging.handlers import RotatingFileHandler

from hsf_app.config import LOG_DIR, LOG_FILE_PATH

_FORMATO = "%(asctime)s | %(levelname)s | %(message)s"


def configurar_logging(nombre_logger: str = "hsf") -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(nombre_logger)
    if logger.handlers:
        return logger  # ya configurado (evita handlers duplicados en re-importes)

    logger.setLevel(logging.DEBUG)

    formato = logging.Formatter(_FORMATO, datefmt="%Y-%m-%d %H:%M:%S")

    handler_archivo = RotatingFileHandler(
        LOG_FILE_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler_archivo.setFormatter(formato)
    handler_archivo.setLevel(logging.DEBUG)

    handler_consola = logging.StreamHandler()
    handler_consola.setFormatter(formato)
    handler_consola.setLevel(logging.INFO)

    logger.addHandler(handler_archivo)
    logger.addHandler(handler_consola)
    return logger
