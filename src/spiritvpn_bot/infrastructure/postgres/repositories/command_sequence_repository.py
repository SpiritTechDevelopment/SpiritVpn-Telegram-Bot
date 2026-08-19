from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from spiritvpn_bot.infrastructure.postgres.models import CommandSequenceRow


class PostgresCommandSequenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def last_issued_for_update(self, customer_id: str) -> int | None:
        result = await self._session.execute(
            select(CommandSequenceRow)
            .where(CommandSequenceRow.customer_id == customer_id)
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        return row.last_command_number if row is not None else None

    async def record(self, customer_id: str, command_number: int) -> None:
        stmt = (
            pg_insert(CommandSequenceRow)
            .values(customer_id=customer_id, last_command_number=command_number)
            .on_conflict_do_update(
                index_elements=[CommandSequenceRow.customer_id],
                set_={"last_command_number": command_number},
            )
        )
        await self._session.execute(stmt)
