"""Configuração estruturada de logs (structlog) para uso em todos os módulos."""

from __future__ import annotations

import logging
import sys

import structlog

from climate_esg.config import get_settings


def configure_logging() -> None:
    """Configura structlog uma vez por processo. Idempotente."""
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=level,
    )

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty()),
        ],
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Atalho para structlog.get_logger com configuração lazy."""
    if not structlog.is_configured():
        configure_logging()
    return structlog.get_logger(name)
