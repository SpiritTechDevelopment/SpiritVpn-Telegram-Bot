from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spiritvpn_bot.application.ports.repositories import (
    CommandSequenceRepository,
    OrderRepository,
)
from spiritvpn_bot.infrastructure.postgres.repositories.command_sequence_repository import (
    PostgresCommandSequenceRepository,
)
from spiritvpn_bot.infrastructure.postgres.repositories.order_repository import (
    PostgresOrderRepository,
)


class SqlAlchemyUnitOfWork:
    """Одна транзакция SQLAlchemy AsyncSession на один use case.

    __aexit__ без предшествующего commit() откатывает — «забыли
    закоммитить» не должно тихо фиксировать частичные изменения, тот же
    принцип, что и у собственной транзакции spiritvpnd.
    """

    # Аннотированы типами портов, а не конкретных Postgres-классов: Protocol
    # с изменяемыми атрибутами проверяется инвариантно, и mypy иначе не
    # признаёт SqlAlchemyUnitOfWork реализацией application.ports.UnitOfWork.
    orders: OrderRepository
    command_sequence: CommandSequenceRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._committed = False

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self._committed = False
        self.orders = PostgresOrderRepository(self._session)
        self.command_sequence = PostgresCommandSequenceRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        try:
            if exc_type is not None or not self._committed:
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()
        self._committed = True

    async def rollback(self) -> None:
        assert self._session is not None
        await self._session.rollback()
