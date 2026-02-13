"""
Centralized logging configuration.

Provides a pre-configured logger factory so every module gets consistent
formatting, level control, and a single place to swap handlers later
(e.g. ship to Datadog, Sentry, CloudWatch).
"""

import logging
import sys
from typing import Optional


_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized = False


def _init_root(level: str = "INFO") -> None:
    """Initialize the root logger once."""
    global _initialized
    if _initialized:
        return

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(handler)

    _initialized = True


def get_logger(name: Optional[str] = None, level: Optional[str] = None) -> logging.Logger:
    """
    Return a logger with the given name.

    On first call the root logger is configured. Subsequent calls reuse the
    same setup so you can safely call ``get_logger(__name__)`` at module level.

    Args:
        name:  Logger name (typically ``__name__``).
        level: Override the log level for *this* logger only.

    Returns:
        A configured ``logging.Logger`` instance.
    """
    # Lazy-import settings to avoid circular deps at module load time.
    try:
        from app.config import settings
        root_level = settings.log_level
    except Exception:
        root_level = "INFO"

    _init_root(root_level)

    logger = logging.getLogger(name)
    if level:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    return logger
