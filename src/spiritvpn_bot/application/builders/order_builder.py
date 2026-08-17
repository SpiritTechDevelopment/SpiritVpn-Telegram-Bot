from __future__ import annotations

from typing import Self

from spiritvpn_bot.application.ports.clock import Clock
from spiritvpn_bot.application.ports.ids import IdGenerator
from spiritvpn_bot.domain.entities.order import Order, OrderStatus
from spiritvpn_bot.domain.entities.plan import Plan


class OrderBuilder:
    """Билдит объект Order из клиента и плана."""

    def __init__(self, id_generator: IdGenerator, clock: Clock) -> None:
        self._id_generator = id_generator
        self._clock = clock
        self._customer_id: str | None = None
        self._plan: Plan | None = None

    def for_customer(self, customer_id: str) -> Self:
        self._customer_id = customer_id
        return self

    def with_plan(self, plan: Plan) -> Self:
        self._plan = plan
        return self

    def build(self) -> Order:
        """Собирает заказ.

        Returns:
            Новый Order в статусе CREATED.

        Raises:
            ValueError: если не были вызваны for_customer() и with_plan().
        """
        if self._customer_id is None or self._plan is None:
            raise ValueError("OrderBuilder requires both for_customer() and with_plan()")
        return Order(
            id=self._id_generator.new_order_id(),
            customer_id=self._customer_id,
            plan=self._plan,
            price=self._plan.price,
            status=OrderStatus.CREATED,
            created_at=self._clock.now(),
        )
