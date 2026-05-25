"""Configuracion de logs para el worker local."""

import logging
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGGER_NAME = "job_watcher.worker"


def _resolve_path(path):
    """Convierte rutas relativas en rutas absolutas dentro del proyecto."""
    target_path = Path(path)

    if target_path.is_absolute():
        return target_path

    return PROJECT_ROOT / target_path


def _get_level(level_name):
    """Convierte el nivel configurado en una constante de logging."""
    return getattr(logging, str(level_name or "INFO").upper(), logging.INFO)


def _remove_existing_handlers(logger):
    """Evita duplicar handlers si setup_logger se llama mas de una vez."""
    for handler in list(logger.handlers):
        if getattr(handler, "_job_watcher_handler", False):
            logger.removeHandler(handler)
            handler.close()


def _mark_handler(handler):
    """Marca un handler como propio del proyecto."""
    handler._job_watcher_handler = True
    return handler


def setup_logger(settings):
    """Configura logs para consola y archivos locales.

    Los archivos .log quedan en la carpeta configurada y no deben subirse a Git.
    Esta funcion no registra credenciales ni datos sensibles.
    """
    logger = logging.getLogger(LOGGER_NAME)
    level = _get_level(settings.get("level", "INFO"))
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.setLevel(level)
    logger.propagate = False
    _remove_existing_handlers(logger)

    console_handler = _mark_handler(logging.StreamHandler())
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if not settings.get("enabled", True):
        return logger

    log_dir = _resolve_path(settings.get("log_dir", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    worker_log_path = log_dir / settings.get("worker_log", "worker.log")
    worker_handler = _mark_handler(
        logging.FileHandler(worker_log_path, encoding="utf-8")
    )
    worker_handler.setLevel(level)
    worker_handler.setFormatter(formatter)
    logger.addHandler(worker_handler)

    error_log_path = log_dir / settings.get("error_log", "errors.log")
    error_handler = _mark_handler(
        logging.FileHandler(error_log_path, encoding="utf-8")
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    return logger
