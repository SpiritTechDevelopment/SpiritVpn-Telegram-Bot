from __future__ import annotations

from spiritvpn_bot.logging import get_logger

logger = get_logger(__name__)


class LoggingEventPublisher:
    """Публикует доменные события в структурированный лог."""

    async def publish(self, event: object) -> None:
        logger.info("domain_event", event_type=type(event).__name__, payload=event)
