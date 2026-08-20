from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spiritvpn_bot.infrastructure.postgres.updates_guard import PostgresUpdatesGuard


async def test_first_seen_update_is_new(session_factory: async_sessionmaker[AsyncSession]) -> None:
    guard = PostgresUpdatesGuard(session_factory)

    assert await guard.mark_if_new(1) is True


async def test_redelivered_update_is_not_new(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    guard = PostgresUpdatesGuard(session_factory)

    first = await guard.mark_if_new(1)
    second = await guard.mark_if_new(1)

    assert first is True
    assert second is False


async def test_survives_across_new_guard_instances(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # Моделирует рестарт процесса: новый инстанс guard'а поверх той же БД.
    await PostgresUpdatesGuard(session_factory).mark_if_new(1)

    result = await PostgresUpdatesGuard(session_factory).mark_if_new(1)

    assert result is False
