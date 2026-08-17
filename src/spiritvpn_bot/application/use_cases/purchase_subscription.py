from __future__ import annotations

from spiritvpn_bot.application.builders.order_builder import OrderBuilder
from spiritvpn_bot.application.ports.clock import Clock
from spiritvpn_bot.application.ports.ids import IdGenerator
from spiritvpn_bot.application.ports.unit_of_work import UnitOfWork
from spiritvpn_bot.domain.entities.order import Order
from spiritvpn_bot.domain.entities.plan import Plan


class PurchaseSubscriptionUseCase:
    """Создаёт заказ и переводит его в AWAITING_PAYMENT."""

    def __init__(self, uow: UnitOfWork, id_generator: IdGenerator, clock: Clock) -> None:
        self._uow = uow
        self._id_generator = id_generator
        self._clock = clock

    async def execute(self, *, customer_id: str, plan: Plan) -> Order:
        """Создаёт заказ на покупку плана.

        Args:
            customer_id: непрозрачный идентификатор клиента.
            plan: план, который покупает клиент.

        Returns:
            Созданный заказ в статусе AWAITING_PAYMENT.
        """
        order = (
            OrderBuilder(self._id_generator, self._clock)
            .for_customer(customer_id)
            .with_plan(plan)
            .build()
        )
        order.mark_awaiting_payment()

        async with self._uow as uow:
            await uow.orders.add(order)
            await uow.commit()

        return order
