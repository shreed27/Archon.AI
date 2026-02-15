"""
Logger configuration for ARCHON.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(log_file: Optional[Path] = None) -> logging.Logger:
    """
    Setup root logger for ARCHON.

    Args:
        log_file: Optional file path for logging

    Returns:
        Configured logger
    """

    logger = logging.getLogger("archon")
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get logger for specific module."""
    return logging.getLogger(f"archon.{name}")
