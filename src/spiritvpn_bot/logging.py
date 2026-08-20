from __future__ import annotations

import logging

import structlog

BoundLogger = structlog.stdlib.BoundLogger


def configure_logging(level: str = "INFO") -> None:
    """Настраивает structlog на JSON-вывод для сбора логов инфрой.

    Вызывается один раз в начале процесса (`__main__.py`), до создания
    контейнера. Все последующие get_logger() в кодовой базе используют
    эту конфигурацию.
    """
    logging.basicConfig(format="%(message)s", level=level.upper())

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> BoundLogger:
    """Возвращает структурированный логгер с именем `name`."""
    return structlog.get_logger(name)
