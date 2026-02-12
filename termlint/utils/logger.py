"""
Root logger configuration
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from termlint.constants import PROJECT_ROOT


def setup_root_logger(
    level: int = logging.INFO,
    log_file: Path | None = None,
    fmt: str = "%(asctime)s [%(name)s] %(levelname)-8s %(message)s",
    datefmt: str = "%Y-%m-%d %H:%M:%S",
) -> logging.Logger:
    """Configures the root logger for the entire project.

    Args:
        level: Logging level (default: logging.INFO).
        log_file: Path to log file (if None, logs only to console).
        fmt: Message format string.
        datefmt: Date format string.
    """
    # Remove any existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Configure handlers
    handlers = [console_handler]
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB per file
            backupCount=5,  # Keep 5 backup copies
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Apply basic configuration
    logging.basicConfig(level=level, handlers=handlers)

    # Silence noisy libraries
    # logging.getLogger("<libname>").setLevel(logging.WARNING)

    return logging.getLogger(" ")


def get_child_logger(file_path: str) -> logging.Logger:
    """
    Get the child logger from root logger by path.

    Args:
        file_path (str): File path (usually __file__ from the calling module)

    Returns:
        Logger: Instance of child logger
    """
    root_logger = setup_root_logger()
    path = Path(file_path)

    if path.is_relative_to(PROJECT_ROOT):
        child_name = str(path.relative_to(PROJECT_ROOT))
    else:
        child_name = str(path)

    child_name = child_name.replace(os.sep, ".")
    if child_name.endswith(".py"):
        child_name = child_name[:-3]

    return root_logger.getChild(child_name)
