from __future__ import annotations

import asyncio

import pytest

from spiritvpn_bot.logging import (
    _format_for_telegram,
    _notify_error_sink,
    configure_logging,
    get_logger,
    set_error_sink,
)


def test_get_logger_returns_a_usable_logger() -> None:
    logger = get_logger(__name__)

    logger.info("test_event", foo="bar")


def test_configure_logging_does_not_raise() -> None:
    configure_logging("DEBUG")

    get_logger(__name__).debug("after_configure")


def test_format_for_telegram_includes_event_and_extra_fields() -> None:
    text = _format_for_telegram(
        {"event": "request_access_failed", "level": "error", "order_id": "order-1"}
    )

    assert "request_access_failed" in text
    assert "order_id: order-1" in text


def test_format_for_telegram_includes_exception_text() -> None:
    text = _format_for_telegram(
        {"event": "boom", "level": "error", "exception": "Traceback...\nValueError: x"}
    )

    assert "Traceback..." in text


class _FakeSink:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send(self, text: str) -> None:
        self.sent.append(text)


@pytest.fixture(autouse=True)
def _reset_error_sink():
    yield
    set_error_sink(None)


async def test_notify_error_sink_schedules_a_send_on_error() -> None:
    sink = _FakeSink()
    set_error_sink(sink)  # type: ignore[arg-type]

    _notify_error_sink(None, "error", {"event": "boom", "level": "error"})
    await asyncio.sleep(0)

    assert len(sink.sent) == 1
    assert "boom" in sink.sent[0]


async def test_notify_error_sink_ignores_info_level() -> None:
    sink = _FakeSink()
    set_error_sink(sink)  # type: ignore[arg-type]

    _notify_error_sink(None, "info", {"event": "boring", "level": "info"})
    await asyncio.sleep(0)

    assert sink.sent == []


def test_notify_error_sink_is_a_noop_without_a_configured_sink() -> None:
    result = _notify_error_sink(None, "error", {"event": "boom", "level": "error"})

    assert result == {"event": "boom", "level": "error"}
