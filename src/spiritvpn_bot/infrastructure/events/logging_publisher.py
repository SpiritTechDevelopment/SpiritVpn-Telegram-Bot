from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


class LoggingEventPublisher:
    """Публикует доменные события в структурированный лог.

    Заглушка первой версии: подписчиков (уведомление в саппорт-чат,
    аналитика, рефералка) пока нет ни одного, поэтому шине пока некому
    рассылать события — только логировать факт. Настоящий pub/sub с
    подписчиками (infrastructure/events/subscribers/) — когда появится
    первый реальный потребитель события; заводить его раньше означало бы
    строить механизм под гипотетических подписчиков.
    """

    async def publish(self, event: object) -> None:
        # "event" — зарезервированное имя первого позиционного аргумента у
        # structlog (сам текст записи), поэтому событие домена передаётся
        # как payload, а не под тем же именем — иначе TypeError на каждый
        # вызов из-за конфликта параметров.
        logger.info("domain_event", event_type=type(event).__name__, payload=event)
