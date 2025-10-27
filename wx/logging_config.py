"""Centralized logging configuration for wx-cli.

This module provides consistent logging setup across all wx-cli modules
with proper formatting, level control, and third-party logger suppression.
"""

import logging
import sys
from typing import Optional

from .constants import DEFAULT_LOG_FORMAT, DEFAULT_LOG_LEVEL, DEBUG_LOG_LEVEL


def setup_logging(level: Optional[str] = None, debug: bool = False) -> None:
    """Configure logging for wx-cli.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses DEFAULT_LOG_LEVEL or DEBUG_LOG_LEVEL based on debug flag.
        debug: If True and level is None, use DEBUG_LOG_LEVEL

    Example:
        >>> setup_logging(debug=True)  # Enable debug logging
        >>> setup_logging(level="WARNING")  # Only warnings and errors
    """
    if level is None:
        level = DEBUG_LOG_LEVEL if debug else DEFAULT_LOG_LEVEL

    # Convert string to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format=DEFAULT_LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stderr)
        ],
        force=True  # Override any existing configuration
    )

    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)

    # Get logger for wx-cli
    logger = logging.getLogger('wx')
    logger.setLevel(numeric_level)

    if debug:
        logger.debug("Debug logging enabled")


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific wx-cli module.

    Args:
        name: Name of the module (e.g., 'wx.radar', 'wx.fetchers')

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Fetching radar data")
    """
    return logging.getLogger(name)


class SensitiveDataFilter(logging.Filter):
    """Logging filter that redacts sensitive information.

    This filter prevents API keys, tokens, and other sensitive data
    from appearing in log messages.
    """

    REDACTION_PATTERNS = [
        ('api_key=', 'api_key=***'),
        ('token=', 'token=***'),
        ('password=', 'password=***'),
        ('secret=', 'secret=***'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and redact log record message.

        Args:
            record: Log record to filter

        Returns:
            Always True (we modify but don't block records)
        """
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            message = record.msg
            for pattern, replacement in self.REDACTION_PATTERNS:
                if pattern in message.lower():
                    # Simple redaction - more sophisticated patterns in security.py
                    record.msg = message.replace(pattern, replacement)
        return True


def add_sensitive_data_filter() -> None:
    """Add sensitive data filter to all handlers.

    Call this after setup_logging() to enable automatic redaction
    of sensitive information in all log messages.
    """
    filter_obj = SensitiveDataFilter()
    root_logger = logging.getLogger()

    for handler in root_logger.handlers:
        handler.addFilter(filter_obj)
