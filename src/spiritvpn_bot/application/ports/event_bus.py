from __future__ import annotations

from typing import Protocol


class EventPublisher(Protocol):
    """Публикация доменных событий.
    """

    async def publish(self, event: object) -> None: ...
