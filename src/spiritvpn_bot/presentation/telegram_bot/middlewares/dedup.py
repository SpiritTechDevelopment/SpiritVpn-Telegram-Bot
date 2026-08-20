from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from spiritvpn_bot.application.ports.updates_guard import UpdatesGuard


class DedupUpdatesMiddleware(BaseMiddleware):
    """Отбрасывает Telegram-апдейт, который уже был обработан."""

    def __init__(self, guard: UpdatesGuard) -> None:
        self._guard = guard

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        assert isinstance(event, Update)
        if not await self._guard.mark_if_new(event.update_id):
            return None
        return await handler(event, data)
