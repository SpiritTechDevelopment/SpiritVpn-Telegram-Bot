from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spiritvpn_bot.infrastructure.postgres.models import ProcessedTelegramUpdateRow


class PostgresUpdatesGuard:
    """UpdatesGuard поверх processed_telegram_updates."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def mark_if_new(self, update_id: int) -> bool:
        stmt = (
            insert(ProcessedTelegramUpdateRow)
            .values(update_id=update_id, processed_at=datetime.now(UTC))
            .on_conflict_do_nothing(index_elements=["update_id"])
            .returning(ProcessedTelegramUpdateRow.update_id)
        )
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.first() is not None
