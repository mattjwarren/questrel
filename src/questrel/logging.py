"""Questrel logging utilities.

AGENTS.md requires detailed logging to a logfile that can be disabled at runtime.
This module provides a single entrypoint to configure logging for the library.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final


LOGGER_NAME: Final[str] = "questrel"


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a Questrel logger.

    The returned logger is always a child of the `questrel` namespace.
    """

    if not name:
        return logging.getLogger(LOGGER_NAME)
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def configure_logging(
    *,
    enabled: bool = True,
    log_file: str | Path = "questrel.log",
    level: int = logging.INFO,
) -> None:
    """Configure library logging.

    - When enabled, logs are written to `log_file`.
    - When disabled, the logger is set to WARNING and no file handler is attached.
    """

    logger = logging.getLogger(LOGGER_NAME)
    logger.propagate = False

    # Remove existing handlers to avoid duplicates when configuring multiple times.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    if not enabled:
        logger.setLevel(logging.WARNING)
        return

    logger.setLevel(level)

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
