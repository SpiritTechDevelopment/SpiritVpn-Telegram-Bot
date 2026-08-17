from __future__ import annotations

from typing import Protocol

from spiritvpn_bot.domain.entities.order import Order


class OrderRepository(Protocol):
    async def add(self, order: Order) -> None: ...

    async def get(self, order_id: str) -> Order | None: ...

    async def get_for_update(self, order_id: str) -> Order | None:
        """Загружает заказ под блокировкой строки (SELECT ... FOR UPDATE).

        Вызывающий метод обязан находиться внутри транзакции UnitOfWork.

        Args:
            order_id: идентификатор заказа.

        Returns:
            Заказ, либо None, если такого заказа нет.
        """
        ...

    async def save(self, order: Order) -> None: ...


class CommandSequenceRepository(Protocol):
    """Владеет монотонным счётчиком command_number на customer_id.
    """

    async def last_issued_for_update(self, customer_id: str) -> int | None:
        """Блокирует и возвращает последний выданный клиенту command_number.

        Args:
            customer_id: ID клиента.

        Returns:
            Последний выданный номер, либо None, если ещё не выдавался.
        """
        ...

    async def record(self, customer_id: str, command_number: int) -> None:
        """Сохраняет command_number как новое последнее выданное значение.

        Должен вызываться в той же транзакции, что и
        last_issued_for_update.

        Args:
            customer_id: непрозрачный идентификатор клиента.
            command_number: номер команды для сохранения.
        """
        ...
