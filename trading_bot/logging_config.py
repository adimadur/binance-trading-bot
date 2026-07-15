"""Logging configuration and redaction helpers."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

LOGGER_NAME = "trading_bot"
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

SENSITIVE_FIELD_NAMES = {
    "api_key",
    "apikey",
    "apiKey",
    "secret",
    "api_secret",
    "apiSecret",
    "signature",
}
REDACTED = "<redacted>"


def redact_sensitive_fields(value: Any) -> Any:
    """Return a copy of nested data with sensitive fields redacted."""
    if isinstance(value, Mapping):
        return {
            key: REDACTED if str(key) in SENSITIVE_FIELD_NAMES else redact_sensitive_fields(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_fields(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive_fields(item) for item in value)
    return value


def setup_logging(log_file: Path = LOG_FILE) -> logging.Logger:
    """Configure and return the application logger."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not any(
        isinstance(handler, logging.FileHandler)
        and Path(handler.baseFilename) == log_file
        for handler in logger.handlers
    ):
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

