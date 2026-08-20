from __future__ import annotations

from spiritvpn_bot.logging import configure_logging, get_logger


def test_get_logger_returns_a_usable_logger() -> None:
    logger = get_logger(__name__)

    logger.info("test_event", foo="bar")


def test_configure_logging_does_not_raise() -> None:
    configure_logging("DEBUG")

    get_logger(__name__).debug("after_configure")
