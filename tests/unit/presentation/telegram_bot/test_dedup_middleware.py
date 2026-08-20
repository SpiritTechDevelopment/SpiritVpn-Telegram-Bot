from __future__ import annotations

from aiogram.types import Update

from spiritvpn_bot.presentation.telegram_bot.middlewares.dedup import DedupUpdatesMiddleware
from tests.unit.application.fakes import InMemoryUpdatesGuard


async def test_first_delivery_reaches_handler() -> None:
    middleware = DedupUpdatesMiddleware(InMemoryUpdatesGuard())
    calls: list[int] = []

    async def handler(event: Update, data: dict[str, object]) -> str:
        calls.append(event.update_id)
        return "handled"

    result = await middleware(handler, Update(update_id=1), {})

    assert result == "handled"
    assert calls == [1]


async def test_redelivered_update_is_skipped() -> None:
    guard = InMemoryUpdatesGuard()
    middleware = DedupUpdatesMiddleware(guard)
    calls: list[int] = []

    async def handler(event: Update, data: dict[str, object]) -> str:
        calls.append(event.update_id)
        return "handled"

    first = await middleware(handler, Update(update_id=7), {})
    second = await middleware(handler, Update(update_id=7), {})

    assert first == "handled"
    assert second is None
    assert calls == [7]
