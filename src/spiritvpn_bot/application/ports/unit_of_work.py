from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from spiritvpn_bot.application.ports.repositories import (
    CommandSequenceRepository,
    OrderRepository,
)


class UnitOfWork(Protocol):
    """Одна транзакция Postgres в рамках одного use case.

    Attributes:
        orders: репозиторий заказов в рамках этой транзакции.
        command_sequence: репозиторий счётчика command_number.
    """

    orders: OrderRepository
    command_sequence: CommandSequenceRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
