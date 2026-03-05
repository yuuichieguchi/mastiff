"""Structured logging setup for mastiff."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the mastiff prefix."""
    return logging.getLogger(f"mastiff.{name}")


def setup_logging(*, verbose: bool = False, log_file: Path | None = None) -> None:
    """Configure logging for mastiff.

    Args:
        verbose: If True, set log level to DEBUG; otherwise INFO.
        log_file: Optional path to a log file for persistent logging.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger("mastiff")
    logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
