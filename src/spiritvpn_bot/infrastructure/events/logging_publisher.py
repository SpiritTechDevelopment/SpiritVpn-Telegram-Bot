from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


class LoggingEventPublisher:
    """Публикует доменные события в структурированный лог."""

    async def publish(self, event: object) -> None:
        logger.info("domain_event", event_type=type(event).__name__, payload=event)
