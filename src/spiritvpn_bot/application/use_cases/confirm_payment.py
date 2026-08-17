from __future__ import annotations

from datetime import timedelta

from spiritvpn_bot.application.errors import OrderNotFound
from spiritvpn_bot.application.ports.clock import Clock
from spiritvpn_bot.application.ports.event_bus import EventPublisher
from spiritvpn_bot.application.ports.unit_of_work import UnitOfWork
from spiritvpn_bot.domain.entities.order import Order
from spiritvpn_bot.domain.events import OrderPaid
from spiritvpn_bot.domain.services.command_sequence import next_command_number


class ConfirmPaymentUseCase:
    """Выдача command_number.
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

            last_issued = await uow.command_sequence.last_issued_for_update(order.customer_id)
            command_number = next_command_number(last_issued)
            expires_at = self._clock.now() + timedelta(days=order.plan.duration_days)

            order.mark_paid(
                command_number=command_number,
                expires_at=expires_at,
                payment_reference=payment_reference,
            )
            await uow.command_sequence.record(order.customer_id, command_number)
            await uow.orders.save(order)
            await uow.commit()

        await self._events.publish(
            OrderPaid(
                order_id=order.id,
                customer_id=order.customer_id,
                plan_id=order.plan.id,
                command_number=command_number,
                expires_at=expires_at,
            )
        )
        return order
