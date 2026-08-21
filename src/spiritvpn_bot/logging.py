from __future__ import annotations

import asyncio
import logging
from collections.abc import MutableMapping
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from spiritvpn_bot.infrastructure.telegram_error_sink import TelegramErrorSink

BoundLogger = structlog.stdlib.BoundLogger

_error_sink: TelegramErrorSink | None = None
_NOTIFIED_METHODS = frozenset({"error", "exception"})


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
            _notify_error_sink,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> BoundLogger:
    """Возвращает структурированный логгер с именем `name`."""
    return structlog.get_logger(name)


def set_error_sink(sink: TelegramErrorSink | None) -> None:
    """Подключает (или отключает) пересылку error/exception-логов в Telegram.

    Args:
        sink: настроенный TelegramErrorSink, либо None — отключить.
    """
    global _error_sink
    _error_sink = sink


def _notify_error_sink(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Structlog processor: на error/exception шлёт копию в Telegram фоновой
    задачей.
    """
    if _error_sink is not None and method_name in _NOTIFIED_METHODS:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            loop.create_task(_safe_send(_error_sink, _format_for_telegram(event_dict)))
    return event_dict


def _format_for_telegram(event_dict: MutableMapping[str, Any]) -> str:
    lines = [f"{event_dict.get('level', 'error').upper()}: {event_dict.get('event', '')}"]
    for key, value in event_dict.items():
        if key not in ("event", "level", "timestamp", "exception"):
            lines.append(f"{key}: {value}")
    exception = event_dict.get("exception")
    if exception:
        lines.append("")
        lines.append(str(exception))
    return "\n".join(lines)


async def _safe_send(sink: TelegramErrorSink, text: str) -> None:
    try:
        await sink.send(text)
    except Exception:  # noqa: BLE001
        pass
