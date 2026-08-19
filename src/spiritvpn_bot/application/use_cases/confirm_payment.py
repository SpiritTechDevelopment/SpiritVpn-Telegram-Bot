from __future__ import annotations

from spiritvpn_bot.application.errors import OrderNotFound
from spiritvpn_bot.application.ports.clock import Clock
from spiritvpn_bot.application.ports.event_bus import EventPublisher
from spiritvpn_bot.application.ports.unit_of_work import UnitOfWork
from spiritvpn_bot.application.use_cases._shared import assign_command_number_and_mark_paid
from spiritvpn_bot.domain.entities.order import Order
from spiritvpn_bot.domain.events import OrderPaid


class ConfirmPaymentUseCase:
    """Выдача command_number для заказа, оплаченного через платёжного провайдера.
    """

    def __init__(self, uow: UnitOfWork, clock: Clock, events: EventPublisher) -> None:
        self._uow = uow
        self._clock = clock
        self._events = events

    async def execute(self, *, order_id: str, payment_reference: str) -> Order:
        """Фиксирует оплату заказа.

        Args:
            order_id: идентификатор оплаченного заказа.
            payment_reference: ссылка на платёж у провайдера оплаты.

        Returns:
            Заказ в статусе PAID с назначенными command_number и expires_at.

        Raises:
            OrderNotFound: если заказа с таким order_id нет.
        """
        async with self._uow as uow:
            order = await uow.orders.get_for_update(order_id)
            if order is None:
                raise OrderNotFound(order_id)

            command_number = await assign_command_number_and_mark_paid(
                uow=uow,
                clock=self._clock,
                order=order,
                payment_reference=payment_reference,
            )
            await uow.orders.save(order)
            await uow.commit()

        assert order.expires_at is not None
        await self._events.publish(
            OrderPaid(
                order_id=order.id,
                customer_id=order.customer_id,
                plan_id=order.plan.id,
                command_number=command_number,
                expires_at=order.expires_at,
            )
        )
        return order
