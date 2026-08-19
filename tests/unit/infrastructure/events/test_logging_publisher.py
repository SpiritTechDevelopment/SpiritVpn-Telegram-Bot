from __future__ import annotations

from dataclasses import dataclass

from spiritvpn_bot.infrastructure.events.logging_publisher import LoggingEventPublisher


@dataclass(frozen=True)
class _FakeEvent:
    order_id: str


async def test_publish_does_not_raise() -> None:
    publisher = LoggingEventPublisher()

    await publisher.publish(_FakeEvent(order_id="order-1"))
