"""Project logging configuration helpers."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from termlint.constants import PROJECT_ROOT


_LOGGER_BASE_NAME = "termlint"
_is_configured = False


def setup_root_logger(
    level: int = logging.WARNING,
    log_file: Path | None = None,
    fmt: str = "%(asctime)s [%(name)s] %(levelname)-8s %(message)s",
    datefmt: str = "%Y-%m-%d %H:%M:%S",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    force: bool = False,
) -> logging.Logger:
    """Configure the application logger once (or force-reconfigure)."""
    global _is_configured

    app_logger = logging.getLogger(_LOGGER_BASE_NAME)
    if _is_configured and not force:
        return app_logger

    app_logger.handlers.clear()
    app_logger.setLevel(level)
    app_logger.propagate = False

    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    app_logger.addHandler(console_handler)

    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        app_logger.addHandler(file_handler)

    _is_configured = True
    return app_logger


def get_child_logger(file_path: str) -> logging.Logger:
    """Return a child logger under the `termlint` namespace."""
    path = Path(file_path)

    if path.is_absolute() and path.is_relative_to(PROJECT_ROOT):
        child_name = str(path.relative_to(PROJECT_ROOT))
    else:
        child_name = str(path)

    child_name = child_name.replace(os.sep, ".")
    if child_name.endswith(".py"):
        child_name = child_name[:-3]
    child_name = child_name.strip(".")

    if not child_name:
        return logging.getLogger(_LOGGER_BASE_NAME)
    return logging.getLogger(f"{_LOGGER_BASE_NAME}.{child_name}")
