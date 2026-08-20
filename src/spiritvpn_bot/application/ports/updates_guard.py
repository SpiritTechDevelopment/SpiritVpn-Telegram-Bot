from __future__ import annotations

from typing import Protocol


class UpdatesGuard(Protocol):
    """Реализация идемпотентности обработки Telegram апдейтов поверх передоставки при рестарте."""

    async def mark_if_new(self, update_id: int) -> bool:
        """Атомарно проверяет и запоминает update_id.

        Returns:
            True, если update_id не встречался раньше (обрабатывать нужно).
            False, если уже был обработан (повторная доставка, пропустить).
        """
        ...
